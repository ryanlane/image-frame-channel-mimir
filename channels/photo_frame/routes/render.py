"""
Rendering (request_image) route for Photo Frame Channel

Provides the POST /request-image endpoint expected by the core platform to obtain a
rendered slideshow frame for a specific resolution and (optionally) gallery/subchannel.

Contract (success): returns raw image bytes (image/jpeg) with headers:
  X-Content-Fingerprint: <fingerprint>
  X-Distribution-Mode: <distribution>
  X-Resolution: <width>x<height>
  (optional) X-Resolution-Fallback: true (when caller omitted resolution)
  Cache-Control: no-store

Error responses are JSON with an HTTP status (400/404/500) and do not return bytes.

"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional, Tuple, Callable, Awaitable

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import Response, JSONResponse

# Service imports (dependency injection expected in channel bootstrap)
try:
    from services import RenderingService, GalleryService, ImageService
except ImportError:  # Fallback when running directly from routes folder
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from services import RenderingService, GalleryService, ImageService


class RenderRoutes:
    """request_image route with dependency injection"""

    def __init__(
        self,
        rendering_service: RenderingService,
        gallery_service: GalleryService,
        image_service: ImageService,
        channel_dir,
        # Optional delegate to the channel instance's async request_image(request_data)
        # When provided, the HTTP route will call into this method so both
        # request-image (HTTP) and request_image (plugin API) share identical logic.
        channel_request_image: Optional[Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None,
    ) -> None:
        self.rendering_service = rendering_service
        self.gallery_service = gallery_service
        self.image_service = image_service
        self.channel_dir = channel_dir
        self.channel_request_image = channel_request_image

    # --------------------------- helpers ---------------------------
    def _derive_resolution(self, payload: Dict[str, Any]) -> Tuple[int, int, bool]:
        settings = payload.get("settings", {}) or {}
        options = payload.get("options", {}) or {}

        fallback = False
        resolution = settings.get("resolution")
        if isinstance(resolution, list) and len(resolution) == 2:
            try:
                w = int(resolution[0])
                h = int(resolution[1])
                if w > 0 and h > 0:
                    return w, h, False
            except (TypeError, ValueError):
                pass

        width = options.get("width")
        height = options.get("height")
        if width and height:
            try:
                w = int(width)
                h = int(height)
                if w > 0 and h > 0:
                    return w, h, False
            except (TypeError, ValueError):
                pass

        # Fallback default
        fallback = True
        return 800, 480, fallback

    def _derive_orientation(self, payload: Dict[str, Any], width: int, height: int) -> str:
        settings = payload.get("settings", {}) or {}
        orientation = settings.get("orientation")
        if isinstance(orientation, str) and orientation in {"landscape", "portrait", "square"}:
            return orientation
        if width == height:
            return "square"
        return "landscape" if width >= height else "portrait"

    def _derive_distribution(self, payload: Dict[str, Any]) -> str:
        settings = payload.get("settings", {}) or {}
        value = settings.get("distribution") or "new"
        return value if isinstance(value, str) else "new"

    def _derive_gallery_id(self, payload: Dict[str, Any]) -> Optional[str]:
        settings = payload.get("settings", {}) or {}
        return settings.get("subChannelId") or payload.get("gallery_id")

    def _hash_bytes(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()[:32]

    # --------------------------- router ---------------------------
    def create_router(self) -> APIRouter:
        router = APIRouter(prefix="", tags=["render"])

        @router.post("/request-image")
        async def request_image(payload: Dict[str, Any] = Body(...)):
            """Generate a slideshow frame image.

            Request JSON schema (tolerant):
            {
              "settings": {
                "resolution": [W, H],
                "orientation": "landscape|portrait|square",
                "distribution": "new|existing",
                "subChannelId": "optional-gallery-id"
              },
              "options": { "width": W, "height": H, "layout": "auto" },
              "gallery_id": "optional-gallery-id"
            }
            """
            try:
                width, height, used_fallback = self._derive_resolution(payload)

                # Basic sanity limits
                if width <= 0 or height <= 0 or width > 8000 or height > 8000:
                    raise HTTPException(status_code=400, detail="invalid_resolution")

                orientation = self._derive_orientation(payload, width, height)
                distribution = self._derive_distribution(payload)
                gallery_id = self._derive_gallery_id(payload)

                # Preferred path: delegate to the channel's request_image for unified logic
                if self.channel_request_image is not None:
                    # Ensure settings exist and include resolved resolution/orientation/distribution
                    req_data: Dict[str, Any] = dict(payload) if isinstance(payload, dict) else {}
                    settings = dict(req_data.get("settings", {}) or {})
                    settings.setdefault("resolution", [width, height])
                    settings.setdefault("orientation", orientation)
                    settings.setdefault("distribution", distribution)
                    req_data["settings"] = settings
                    if gallery_id and not req_data.get("gallery_id"):
                        req_data["gallery_id"] = gallery_id

                    # Ask channel for bytes-first response
                    req_data.setdefault("include_base64", False)

                    result = await self.channel_request_image(req_data)
                    if not result or not result.get("success"):
                        # Map common errors to HTTP codes
                        detail = (result or {}).get("error") if isinstance(result, dict) else None
                        status = 404 if detail in {"No images available", "no_content", "Render failed"} else 500
                        return JSONResponse(status_code=status, content={
                            "success": False,
                            "error": detail or "render_failure",
                        })

                    # Extract bytes (prefer direct bytes; fallback to base64 if present)
                    content_bytes: Optional[bytes] = result.get("bytes")  # type: ignore[assignment]
                    if content_bytes is None and isinstance(result.get("image"), str):
                        import base64 as _b64
                        try:
                            content_bytes = _b64.b64decode(result["image"])  # type: ignore[index]
                        except Exception:
                            content_bytes = b""
                    if not content_bytes:
                        return JSONResponse(status_code=500, content={
                            "success": False,
                            "error": "empty_bytes",
                        })

                    content_type = result.get("content_type") or "image/jpeg"
                    fingerprint = self._hash_bytes(content_bytes)
                    res_w = int(result.get("width") or width)
                    res_h = int(result.get("height") or height)
                    headers = {
                        "X-Content-Fingerprint": fingerprint,
                        "X-Distribution-Mode": (result.get("distribution_mode") or distribution),
                        "X-Resolution": f"{res_w}x{res_h}",
                        "Cache-Control": "no-store",
                    }
                    if used_fallback:
                        headers["X-Resolution-Fallback"] = "true"

                    return Response(content=content_bytes, media_type=str(content_type), headers=headers)

                # Fallback path: legacy service-based rendering (kept for backward-compat)
                rel_path = await self.rendering_service.render_image(
                    resolution=(width, height),
                    orientation=orientation,
                    settings=payload.get("settings", {}),
                    subchannel_id=gallery_id,
                    gallery_service=self.gallery_service,
                    image_service=self.image_service,
                )

                from pathlib import Path

                absolute_path = Path(self.channel_dir) / rel_path
                if not absolute_path.exists():
                    return JSONResponse(
                        status_code=404,
                        content={
                            "success": False,
                            "error": "no_content",
                            "message": "Rendered image not found",
                        },
                    )

                data = absolute_path.read_bytes()
                fingerprint = self._hash_bytes(data)

                headers = {
                    "X-Content-Fingerprint": fingerprint,
                    "X-Distribution-Mode": distribution,
                    "X-Resolution": f"{width}x{height}",
                    "Cache-Control": "no-store",
                }
                if used_fallback:
                    headers["X-Resolution-Fallback"] = "true"

                return Response(content=data, media_type="image/jpeg", headers=headers)

            except HTTPException:
                raise
            except Exception as e:  # noqa: BLE001
                return JSONResponse(
                    status_code=500,
                    content={
                        "success": False,
                        "error": "render_failure",
                        "message": str(e),
                    },
                )

        return router


def create_render_router(
    rendering_service: RenderingService,
    gallery_service: GalleryService,
    image_service: ImageService,
    channel_dir,
    channel_request_image: Optional[Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None,
) -> APIRouter:
    routes = RenderRoutes(
        rendering_service=rendering_service,
        gallery_service=gallery_service,
        image_service=image_service,
        channel_dir=channel_dir,
        channel_request_image=channel_request_image,
    )
    return routes.create_router()


# Backward-compatible default router (unbound dependencies)
router = APIRouter()  # Will be bound in channel initialization
