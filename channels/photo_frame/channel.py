import os
import json
import asyncio
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, Optional, List
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
from .utils.image_processor import ImageProcessor
from .utils.database import PhotoFrameDB

app = FastAPI()

class PhotoFrameChannel:
    """
    Photo Frame channel for Mimir Platform
    Provides digital photo frame functionality with intelligent image management
    """
    def __init__(self, channel_dir: str):
        self.channel_dir = Path(channel_dir)
        self.config_path = self.channel_dir / "config.json"
        self.config = self._load_config()
        self.db = PhotoFrameDB(self.channel_dir / "data" / "photo_frame.db")
        self.image_processor = ImageProcessor(
            upload_dir=self.channel_dir / "assets" / "uploads",
            thumb_dir=self.channel_dir / "data" / "thumbs"
        )
        self.last_update = None
        self.last_error = None
        self.current_image_id = None
        self._ensure_directories()

    def _load_config(self) -> Dict[str, Any]:
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def _ensure_directories(self):
        dirs = [
            self.channel_dir / "assets" / "uploads",
            self.channel_dir / "data" / "thumbs",
            self.channel_dir / "data"
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

    @property
    def id(self) -> str:
        return "photo_frame"

    async def render_image(self, resolution: Tuple[int, int], orientation: str, settings: Dict[str, Any]) -> str:
        try:
            image_record = await self._get_next_image(settings)
            if not image_record:
                return self.config["placeholder_image"]
            output_path = await self._process_image_for_display(image_record, resolution, orientation, settings)
            await self._update_image_stats(image_record["id"])
            self.current_image_id = image_record["id"]
            self.last_update = datetime.now(timezone.utc)
            self.last_error = None
            return self.config["current_image"]
        except Exception as e:
            self.last_error = str(e)
            return await self._get_fallback_image()

    async def _get_next_image(self, settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not settings.get("slideshow_enabled", True):
            if self.current_image_id:
                return self.db.get_image(self.current_image_id)
        order_mode = settings.get("order_mode", "added")
        enabled_images = self.db.get_enabled_images()
        if not enabled_images:
            return None
        if order_mode == "random":
            import random
            return random.choice(enabled_images)
        elif order_mode == "custom":
            return self._get_next_by_custom_order(enabled_images)
        else:
            return self._get_next_by_date_added(enabled_images)

    async def _process_image_for_display(self, image_record: Dict[str, Any], resolution: Tuple[int, int], orientation: str, settings: Dict[str, Any]) -> str:
        source_path = self.channel_dir / "assets" / "uploads" / image_record["filename"]
        output_path = self.channel_dir / self.config["current_image"]
        crop_mode = settings.get("crop_mode", "smart_crop")
        if crop_mode == "smart_crop":
            await self.image_processor.render_with_crop(
                source_path=source_path,
                output_path=output_path,
                resolution=resolution,
                crop_x=image_record.get("crop_x", 0),
                crop_y=image_record.get("crop_y", 0),
                crop_width=image_record.get("crop_width", 100),
                crop_height=image_record.get("crop_height", 100)
            )
        elif crop_mode == "letterbox":
            await self.image_processor.render_letterbox(
                source_path=source_path,
                output_path=output_path,
                resolution=resolution
            )
        else:
            await self.image_processor.render_stretch(
                source_path=source_path,
                output_path=output_path,
                resolution=resolution
            )
        return str(output_path)

    async def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, str]:
        errors = {}
        valid_orders = ["added", "random", "custom"]
        if settings.get("order_mode") not in valid_orders:
            errors["order_mode"] = f"Must be one of: {', '.join(valid_orders)}"
        valid_crops = ["smart_crop", "letterbox", "stretch"]
        if settings.get("crop_mode") not in valid_crops:
            errors["crop_mode"] = f"Must be one of: {', '.join(valid_crops)}"
        return errors

    def get_status(self) -> Dict[str, Any]:
        image_count = self.db.get_image_count()
        enabled_count = self.db.get_enabled_image_count()
        return {
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "last_error": self.last_error,
            "current_image_id": self.current_image_id,
            "total_images": image_count,
            "enabled_images": enabled_count,
            "database_ok": self.db.check_health(),
            "storage_usage": self._get_storage_usage()
        }

    def _get_storage_usage(self) -> Dict[str, Any]:
        uploads_dir = self.channel_dir / "assets" / "uploads"
        thumbs_dir = self.channel_dir / "data" / "thumbs"
        def dir_size(path):
            if not path.exists():
                return 0
            return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        return {
            "uploads_mb": round(dir_size(uploads_dir) / 1024 / 1024, 2),
            "thumbs_mb": round(dir_size(thumbs_dir) / 1024 / 1024, 2),
            "total_mb": round((dir_size(uploads_dir) + dir_size(thumbs_dir)) / 1024 / 1024, 2)
        }

    async def _get_fallback_image(self) -> str:
        if self.current_image_id and os.path.exists(self.config["current_image"]):
            return self.config["current_image"]
        images = self.db.get_enabled_images()
        if images:
            return await self._render_simple_fallback(images[0])
        return self.config["placeholder_image"]

# Instantiate channel
channel = PhotoFrameChannel(os.path.dirname(__file__))

@app.get("/api/channels/com.epaperframe.photoframe/image")
async def get_current_image():
    return FileResponse(str(channel.channel_dir / channel.config["current_image"]))

@app.get("/api/channels/com.epaperframe.photoframe/status")
async def get_status():
    return JSONResponse(channel.get_status())

@app.post("/api/channels/com.epaperframe.photoframe/update")
async def manual_update():
    # Example: trigger image update
    settings = channel.db.get_settings()
    resolution = (800, 600)  # Example default
    orientation = "landscape"
    await channel.render_image(resolution, orientation, settings)
    return JSONResponse({"success": True})

@app.get("/api/channels/com.epaperframe.photoframe/images")
async def list_images():
    images = channel.db.get_all_images()
    return JSONResponse(images)

@app.post("/api/channels/com.epaperframe.photoframe/upload")
async def upload_images(files: List[UploadFile] = File(...)):
    results = []
    for file in files:
        try:
            image_data = await channel.image_processor.save_upload(file)
            image_id = channel.db.add_image(image_data)
            results.append({"filename": file.filename, "success": True, "image_id": image_id})
        except Exception as e:
            results.append({"filename": file.filename, "success": False, "error": str(e)})
    return JSONResponse({"results": results})

@app.delete("/api/channels/com.epaperframe.photoframe/images/{image_id}")
async def delete_image(image_id: int):
    success = await channel.db.delete_image(image_id)
    if success:
        return JSONResponse({"success": True})
    else:
        return JSONResponse({"success": False, "error": "Image not found"}, status_code=404)

@app.put("/api/channels/com.epaperframe.photoframe/images/{image_id}")
async def update_image(
    image_id: int,
    title: str = Form(""),
    description: str = Form(""),
    crop_x: float = Form(0),
    crop_y: float = Form(0),
    crop_width: float = Form(100),
    crop_height: float = Form(100),
    preserve_aspect_ratio: bool = Form(False)
):
    success = channel.db.update_image(image_id, {
        "title": title,
        "description": description,
        "crop_x": crop_x,
        "crop_y": crop_y,
        "crop_width": crop_width,
        "crop_height": crop_height,
        "preserve_aspect_ratio": preserve_aspect_ratio
    })
    if success:
        return JSONResponse({"success": True})
    else:
        return JSONResponse({"success": False, "error": "Image not found"}, status_code=404)

@app.get("/api/channels/com.epaperframe.photoframe/settings")
async def get_settings():
    return JSONResponse(channel.db.get_settings())

@app.put("/api/channels/com.epaperframe.photoframe/settings")
async def update_settings(settings: Dict[str, Any]):
    errors = await channel.validate_settings(settings)
    if errors:
        return JSONResponse({"success": False, "errors": errors}, status_code=400)
    channel.db.update_settings(settings)
    return JSONResponse({"success": True})

@app.get("/api/channels/com.epaperframe.photoframe/hardware")
async def get_hardware():
    # Mocked hardware info for development
    return JSONResponse({"display": "Inky", "resolution": [800, 600], "orientation": "landscape"})
