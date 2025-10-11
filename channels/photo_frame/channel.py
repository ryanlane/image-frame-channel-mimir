import os
import sys
import json
import asyncio
import re
import random
import shutil
import time
import base64
"""
Photo Frame Channel for Mimir Platform v2.4+ with Gallery Support

REFACTORING STATUS: ✅ COMPLETE
✅ MODELS: Extracted to models/ directory
  - models/gallery.py: Gallery data models and operations
  - models/image.py: Image metadata and upload handling  
  - models/settings.py: Settings validation and management

✅ SERVICES: Extracted to services/ directory
  - services/gallery_service.py: Gallery business logic
  - services/image_service.py: Image processing and metadata
  - services/rendering_service.py: Display rendering logic
  - services/storage_service.py: File and data management

✅ ROUTES: Extracted to routes/ directory  
  - routes/images.py: Image upload, management, and reordering
  - routes/galleries.py: Gallery (sub-channel) operations
  - routes/settings.py: Configuration management
  - routes/assets.py: Static file serving
  - routes/admin.py: Administrative operations

This channel provides digital photo frame functionality with intelligent image management and galleries.
Architecture: Modular FastAPI design with dependency injection and service layer separation.
"""

from datetime import datetime, timezone
from typing import Tuple, Dict, Any, Optional, List
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, Optional, List
from pathlib import Path
import sys
import importlib.util
import traceback
import logging
import types
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse

_PLUGIN_DIR = Path(__file__).parent

logger = logging.getLogger("mimir.channels.photoframe")
if not logger.handlers:
    # Basic config only if root not already configured
    logging.basicConfig(level=logging.INFO)

def _import_local(module_key: str, rel_path: str):
    """Import a sibling module by explicit file path with pre-registration.

    Provides deterministic, package-independent loading so dynamic discovery
    (importlib.spec_from_file_location) doesn't break relative imports or
    decorator introspection (e.g. @dataclass) which expects the module present
    in sys.modules during class creation.
    """
    target = _PLUGIN_DIR / rel_path
    if not target.exists():
        raise ImportError(f"PhotoFrame: module file not found: {rel_path}")
    unique_name = f"photoframe_{module_key}"
    if unique_name in sys.modules:
        return sys.modules[unique_name]
    spec = importlib.util.spec_from_file_location(unique_name, target)
    if spec is None or spec.loader is None:
        raise ImportError(f"PhotoFrame: cannot create spec for {rel_path}")
    module = importlib.util.module_from_spec(spec)
    # Pre-register so decorators can resolve module
    sys.modules[unique_name] = module
    try:
        spec.loader.exec_module(module)  # type: ignore[attr-defined]
    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()
        # Cleanup failed registration to avoid poisoning
        sys.modules.pop(unique_name, None)
        raise ImportError(f"PhotoFrame: failed importing {rel_path}: {e}\n{tb}") from e
    return module

# ---------------------------------------------------------------------------
# MODELS
try:
    # Prefer aggregated __init__.py if present
    models_mod = _import_local("models", "models/__init__.py") if (_PLUGIN_DIR / "models" / "__init__.py").exists() else None
except Exception as e:  # noqa: BLE001
    logger.error("[PhotoFrame] Failed loading models package: %s", e)
    models_mod = None

if models_mod is None:
    # Fallback: load individual model files (best-effort)
    try:
        gallery_model = _import_local("models_gallery", "models/gallery.py")
        image_model = _import_local("models_image", "models/image.py")
        settings_model = _import_local("models_settings", "models/settings.py")
    except Exception as e:  # noqa: BLE001
        logger.error("[PhotoFrame] Critical: unable to load required model modules: %s", e)
        raise
    # Aggregate symbols (guard with getattr to avoid crashing if later additions missing)
    Gallery = getattr(gallery_model, "Gallery")  # type: ignore
    GalleryCreate = getattr(gallery_model, "GalleryCreate")  # type: ignore
    GalleryUpdate = getattr(gallery_model, "GalleryUpdate")  # type: ignore
    Image = getattr(image_model, "Image")  # type: ignore
    ImageMetadata = getattr(image_model, "ImageMetadata")  # type: ignore
    ImageUploadResult = getattr(image_model, "ImageUploadResult")  # type: ignore
    ImageBatchUploadResult = getattr(image_model, "ImageBatchUploadResult")  # type: ignore
    ChannelSettings = getattr(settings_model, "ChannelSettings")  # type: ignore
    GallerySettings = getattr(settings_model, "GallerySettings")  # type: ignore
    SettingsManager = getattr(settings_model, "SettingsManager")  # type: ignore
else:
    try:
        Gallery = getattr(models_mod, "Gallery")  # type: ignore
        GalleryCreate = getattr(models_mod, "GalleryCreate")  # type: ignore
        GalleryUpdate = getattr(models_mod, "GalleryUpdate")  # type: ignore
        Image = getattr(models_mod, "Image")  # type: ignore
        ImageMetadata = getattr(models_mod, "ImageMetadata")  # type: ignore
        ImageUploadResult = getattr(models_mod, "ImageUploadResult")  # type: ignore
        ImageBatchUploadResult = getattr(models_mod, "ImageBatchUploadResult")  # type: ignore
        ChannelSettings = getattr(models_mod, "ChannelSettings")  # type: ignore
        GallerySettings = getattr(models_mod, "GallerySettings")  # type: ignore
        SettingsManager = getattr(models_mod, "SettingsManager")  # type: ignore
    except Exception as e:  # noqa: BLE001
        logger.error("[PhotoFrame] Failed binding model attributes: %s", e)
        raise

# ---------------------------------------------------------------------------
# SERVICES (with isolated 'models' alias injection to prevent cross-channel collisions)
_prev_models_alias = sys.modules.get("models")
try:  # Temporarily map 'models' to this channel's model definitions so service files using 'from models import ...' resolve locally
    if models_mod is not None:
        sys.modules["models"] = models_mod
    else:
        temp_models = types.ModuleType("models")
        for _name, _val in [
            ("Gallery", Gallery),
            ("GalleryCreate", GalleryCreate),
            ("GalleryUpdate", GalleryUpdate),
            ("Image", Image),
            ("ImageMetadata", ImageMetadata),
            ("ImageUploadResult", ImageUploadResult),
            ("ImageBatchUploadResult", ImageBatchUploadResult),
            ("ChannelSettings", ChannelSettings),
            ("GallerySettings", GallerySettings),
            ("SettingsManager", SettingsManager),
        ]:
            setattr(temp_models, _name, _val)
        sys.modules["models"] = temp_models

    gallery_service_mod = _import_local("service_gallery", "services/gallery_service.py")
    image_service_mod = _import_local("service_image", "services/image_service.py")
    rendering_service_mod = _import_local("service_rendering", "services/rendering_service.py")
    storage_service_mod = _import_local("service_storage", "services/storage_service.py")
    GalleryService = getattr(gallery_service_mod, "GalleryService")  # type: ignore
    ImageService = getattr(image_service_mod, "ImageService")  # type: ignore
    RenderingService = getattr(rendering_service_mod, "RenderingService")  # type: ignore
    StorageService = getattr(storage_service_mod, "StorageService")  # type: ignore
except Exception as e:  # noqa: BLE001
    logger.error("[PhotoFrame] Failed loading service modules: %s", e)
    raise
finally:
    # Restore prior 'models' module to avoid affecting other plugins (e.g., spotify_status)
    if _prev_models_alias is not None:
        sys.modules["models"] = _prev_models_alias
    else:
        sys.modules.pop("models", None)

# ---------------------------------------------------------------------------
# ROUTES (individual modules exposing factory functions)
# Some legacy route modules still do 'from services import X' / 'from models import Y'.
# We create temporary per-channel aliases to prevent resolving another plugin's
# similarly named global modules.
_prev_services_alias_routes = sys.modules.get("services")
_prev_models_alias_routes = sys.modules.get("models")
try:
    # Inject models alias (again) for route module import phase
    if models_mod is not None:
        sys.modules["models"] = models_mod
    else:
        temp_models_routes = types.ModuleType("models")
        for _name, _val in [
            ("Gallery", Gallery),
            ("GalleryCreate", GalleryCreate),
            ("GalleryUpdate", GalleryUpdate),
            ("Image", Image),
            ("ImageMetadata", ImageMetadata),
            ("ImageUploadResult", ImageUploadResult),
            ("ImageBatchUploadResult", ImageBatchUploadResult),
            ("ChannelSettings", ChannelSettings),
            ("GallerySettings", GallerySettings),
            ("SettingsManager", SettingsManager),
        ]:
            setattr(temp_models_routes, _name, _val)
        sys.modules["models"] = temp_models_routes

    # Inject services alias with service class references
    temp_services_routes = types.ModuleType("services")
    for _name, _val in [
        ("GalleryService", GalleryService),
        ("ImageService", ImageService),
        ("RenderingService", RenderingService),
        ("StorageService", StorageService),
    ]:
        setattr(temp_services_routes, _name, _val)
    sys.modules["services"] = temp_services_routes

    images_routes_mod = _import_local("routes_images", "routes/images.py")
    galleries_routes_mod = _import_local("routes_galleries", "routes/galleries.py")
    settings_routes_mod = _import_local("routes_settings", "routes/settings.py")
    assets_routes_mod = _import_local("routes_assets", "routes/assets.py")
    admin_routes_mod = _import_local("routes_admin", "routes/admin.py")
    # Newly added render (request_image) route module
    try:
        render_routes_mod = _import_local("routes_render", "routes/render.py")
    except Exception as e:  # noqa: BLE001
        logger.error("[PhotoFrame] Failed loading render route module: %s", e)
        render_routes_mod = None
    # Optional legacy or subchannel settings modules
    legacy_assets_factory = getattr(assets_routes_mod, "create_legacy_assets_router", None)
    create_images_router = getattr(images_routes_mod, "create_images_router")  # type: ignore
    create_galleries_router = getattr(galleries_routes_mod, "create_galleries_router")  # type: ignore
    create_settings_router = getattr(settings_routes_mod, "create_settings_router")  # type: ignore
    create_assets_router = getattr(assets_routes_mod, "create_assets_router")  # type: ignore
    create_legacy_assets_router = legacy_assets_factory if legacy_assets_factory else (lambda *a, **k: APIRouter())
    create_admin_router = getattr(admin_routes_mod, "create_admin_router")  # type: ignore
    # Subchannel settings (may be in settings or separate file)
    create_subchannel_settings_router = getattr(settings_routes_mod, "create_subchannel_settings_router", lambda *a, **k: APIRouter())  # type: ignore
    # Render router factory (may be None if import failed)
    create_render_router = getattr(render_routes_mod, "create_render_router", lambda *a, **k: APIRouter()) if render_routes_mod else (lambda *a, **k: APIRouter())
except Exception as e:  # noqa: BLE001
    logger.error("[PhotoFrame] Failed loading route modules: %s", e)
    raise
finally:
    # Restore prior modules to avoid polluting global import space
    if _prev_services_alias_routes is not None:
        sys.modules["services"] = _prev_services_alias_routes
    else:
        sys.modules.pop("services", None)
    if _prev_models_alias_routes is not None:
        sys.modules["models"] = _prev_models_alias_routes
    else:
        sys.modules.pop("models", None)

# ---------------------------------------------------------------------------
# UTILS
try:
    image_processor_mod = _import_local("utils_image_processor", "utils/image_processor.py")
    file_metadata_mod = _import_local("utils_file_metadata", "utils/file_metadata.py")
    ImageProcessor = getattr(image_processor_mod, "ImageProcessor")  # type: ignore
    FileMetadataManager = getattr(file_metadata_mod, "FileMetadataManager")  # type: ignore
except Exception as e:  # noqa: BLE001
    logger.error("[PhotoFrame] Failed loading utility modules: %s", e)
    raise
class BaseChannel:
    """
    Abstract base class for Mimir Platform channels with sub-channel support
    """
    
    def supports_subchannels(self) -> bool:
        """Return whether this channel supports sub-channels"""
        return False
    
    def get_subchannel_config(self) -> Dict[str, Any]:
        """Get sub-channel configuration"""
        return {"enabled": False}
    
    def get_subchannels(self) -> List[Dict[str, Any]]:
        """Get list of sub-channels"""
        return []
    
    def create_subchannel(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new sub-channel"""
        raise NotImplementedError("Channel does not support sub-channels")
    
    def update_subchannel(self, subchannel_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing sub-channel"""
        raise NotImplementedError("Channel does not support sub-channels")
    
    def delete_subchannel(self, subchannel_id: str) -> bool:
        """Delete a sub-channel"""
        raise NotImplementedError("Channel does not support sub-channels")
    
    def assign_content_to_subchannel(self, subchannel_id: str, content_ids: List[str], action: str = "add") -> bool:
        """Assign content to a sub-channel"""
        raise NotImplementedError("Channel does not support sub-channels")
    
    def get_subchannel_content(self, subchannel_id: str, limit: int = None, offset: int = None) -> Dict[str, Any]:
        """Get content from a sub-channel"""
        raise NotImplementedError("Channel does not support sub-channels")
    
    def _generate_subchannel_id(self, name: str) -> str:
        """Generate unique ID from name"""
        # Clean the name
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', name).lower()
        base_id = re.sub(r'\s+', '_', clean_name.strip())
        
        # Check for duplicates in sub-channels
        existing_ids = {subchannel['id'] for subchannel in self.get_subchannels()}
        
        if base_id not in existing_ids:
            return base_id
        
        # Add suffix for duplicates
        counter = 1
        while f"{base_id}_{counter}" in existing_ids:
            counter += 1
        return f"{base_id}_{counter}"

class PhotoFrameChannel(BaseChannel):
    """
    Photo Frame channel for Mimir Platform v2.4+ with Gallery Support
    Provides digital photo frame functionality with intelligent image management and galleries
    
    ⚠️ CRITICAL: API INTEGRATION NOTES ⚠️
    ==========================================
    This channel integrates with the centralized Mimir API at:
    - Base API: /api/channels/com.epaperframe.photoframe/
    - Channel ID: com.epaperframe.photoframe (from config.json)
    - Directory: /var/opt/mimir/mimir-api/channels/photo_frame/
    
    All paths and endpoints must use the channel discovery service for proper resolution.
    Never hardcode paths - always use dynamic resolution through the API.
    """
    
    def __init__(self, channel_dir: str):
        """
        Initialize Photo Frame Channel
        
        Args:
            channel_dir: Path to channel directory (resolved by ChannelDiscoveryService)
                        Should be: /var/opt/mimir/mimir-api/channels/photo_frame/
        """
        self.channel_dir = Path(channel_dir)
        self.config_path = self.channel_dir / "config.json"
        self._config = self._load_config()
        
        # Validate critical paths for API integration
        self._validate_api_integration()
        
        # Initialize components - Pure JSON storage
        # Use file-based metadata for images
        self.metadata = FileMetadataManager(self.channel_dir / "assets" / "uploads")
        
        # Image processor with new thumbnail approach
        self.image_processor = ImageProcessor(
            upload_dir=self.channel_dir / "assets" / "uploads"
        )
        
        # Gallery management is now handled by GalleryService
        
        # State tracking
        self.last_update = None
        self.last_error = None
        self.current_image_id = None
        
        # Distribution state tracking - maps gallery_id to last selected image_id
        self._last_selected_by_gallery = {}
        
        # NEW: Initialize services for improved architecture
        self.settings_manager = SettingsManager()  # Add missing settings manager
        self.gallery_service = GalleryService(self.channel_dir)
        self.image_service = ImageService(
            self.channel_dir, 
            self.metadata,
            self.image_processor
        )
        # Pass image_processor so render pipeline can actually crop/resize
        self.rendering_service = RenderingService(self.channel_dir, self.image_processor)
        self.storage_service = StorageService(self.channel_dir)

        # Render cache: (gallery_key, width, height, orientation, crop_mode) -> entry
        # Used to reuse processed images when distribution_mode == "current" or rapid repeats occur.
        self._render_cache = {}
        self._cache_ttl_seconds = 300  # basic TTL; can be made configurable
        
        # Ensure directories exist
        self._ensure_directories()
        logger.info(
            "[PhotoFrame] Initialized channel directory=%s id=%s api_base=/api/channels/%s/",
            self.channel_dir,
            self.id,
            self.id,
        )
    
    def _validate_api_integration(self):
        """Validate that the channel is properly set up for API integration"""
        # Check config exists and has correct ID
        if not self.config_path.exists():
            raise RuntimeError(f"config.json not found at {self.config_path}")
        
        config = self._load_config()
        expected_id = "com.epaperframe.photoframe"
        actual_id = config.get("id")
        
        if actual_id != expected_id:
            print(f"⚠️  WARNING: Channel ID mismatch!")
            print(f"   Expected: {expected_id}")
            print(f"   Actual: {actual_id}")
            print(f"   This may cause API routing issues.")
        
        # Check critical directories with better error handling
        required_dirs = [
            self.channel_dir / "assets" / "uploads",
            self.channel_dir / "data"
        ]
        
        for dir_path in required_dirs:
            if not dir_path.exists():
                try:
                    print(f"📁 Creating required directory: {dir_path}")
                    dir_path.mkdir(parents=True, exist_ok=True)
                except PermissionError as e:
                    print(f"❌ Permission denied creating {dir_path}: {e}")
                    print(f"   Please ensure the API service has write permissions to {dir_path.parent}")
                    raise RuntimeError(f"Cannot create required directory {dir_path}: {e}")
                except Exception as e:
                    print(f"❌ Failed to create directory {dir_path}: {e}")
                    raise RuntimeError(f"Cannot create required directory {dir_path}: {e}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load channel configuration"""
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    def _ensure_directories(self):
        """Create necessary directories"""
        dirs = [
            self.channel_dir / "assets" / "uploads",
            self.channel_dir / "data" / "thumbs",
            self.channel_dir / "data"
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    @property
    def id(self) -> str:
        """Channel identifier"""
        return self._config.get("id", "com.epaperframe.photoframe")
    
    @property 
    def config(self) -> dict:
        """Channel configuration"""
        return self._config
    
    async def render_image(self, resolution: tuple, orientation: str = "landscape", settings: dict = None, subchannel_id: str = None):
        """
        Render image for specific display resolution using resolution-based folder structure.
        Creates images in current/{width}x{height}/ subfolders for efficient sharing.
        
        Args:
            resolution: (width, height) in pixels
            orientation: "landscape" or "portrait"
            settings: User configuration from Mimir Platform (deprecated - use gallery settings)
            subchannel_id: Gallery ID to select from (for proper settings)
        """
        try:
            # Create resolution-specific directory
            width, height = resolution
            resolution_folder = f"{width}x{height}"
            resolution_dir = self.channel_dir / "current" / resolution_folder
            resolution_dir.mkdir(parents=True, exist_ok=True)
            
            # Set output path for this resolution
            output_path = resolution_dir / "current.jpg"
            
            print(f"🎯 Rendering image for photo frame at resolution {width}x{height}")
            if subchannel_id:
                print(f"📁 Using gallery: {subchannel_id}")
            
            # Get settings from gallery if specified, otherwise use global settings
            if subchannel_id:
                try:
                    current_settings = self.gallery_service.get_gallery_settings(subchannel_id)
                    print(f"📋 Using gallery-specific settings: {current_settings}")
                except ValueError:
                    print(f"⚠️ Gallery '{subchannel_id}' not found, using global settings")
                    current_settings = settings or {}
            else:
                current_settings = settings or {}

            all_images = self.metadata.get_all_images()

            # Get next image based on gallery selection or all images
            if subchannel_id:
                image_record = self.gallery_service.get_next_image_from_gallery(
                    subchannel_id, all_images, current_settings, self.image_service
                )
                if not image_record:
                    print(f"⚠️ Gallery '{subchannel_id}' not found or has no images, falling back to all images")
                    image_record = self.image_service.get_next_image(current_settings)
            else:
                image_record = self.image_service.get_next_image(current_settings)
            
            if not image_record:
                # No images available, use placeholder
                placeholder_path = self.channel_dir / "placeholder.jpg"
                if placeholder_path.exists():
                    # Process placeholder for this resolution
                    await self._process_placeholder_for_display(
                        placeholder_path, output_path, resolution, current_settings
                    )
                    print(f"✅ Used placeholder image for {resolution_folder}")
                    return str(output_path)
                else:
                    raise Exception("No images available and no placeholder found")
            
            # Process image for display
            await self._process_image_for_display(
                image_record, resolution, orientation, current_settings
            )
            
            # Copy the processed image to our resolution-specific location
            legacy_current = self.channel_dir / self.config["current_image"]
            if legacy_current.exists():
                shutil.copy2(legacy_current, output_path)
                print(f"✅ Generated {resolution_folder}/current.jpg ({output_path.stat().st_size} bytes)")
            
            # Update statistics (important for slideshow rotation)
            await self._update_image_stats(image_record["id"])
            
            # Update state tracking
            self.current_image_id = image_record["id"]
            self.last_update = datetime.now(timezone.utc)
            self.last_error = None
            
            return str(output_path)
            
        except Exception as e:
            print(f"❌ Failed to render image for resolution {resolution}: {e}")
            self.last_error = str(e)
            
            # Try to fall back to placeholder
            try:
                placeholder_path = self.channel_dir / "placeholder.jpg"
                if placeholder_path.exists():
                    shutil.copy2(placeholder_path, output_path)
                    print(f"🔄 Used placeholder as fallback for {resolution_folder}")
                    return str(output_path)
            except Exception as fallback_error:
                print(f"❌ Fallback also failed: {fallback_error}")
            
            # Return fallback image using existing logic
            return await self._get_fallback_image()
    
    async def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, str]:
        """Validate channel settings"""
        errors = {}
        
        # Validate order_mode (only if present)
        if "order_mode" in settings:
            valid_orders = ["added", "random", "custom"]
            if settings.get("order_mode") not in valid_orders:
                errors["order_mode"] = f"Must be one of: {', '.join(valid_orders)}"
        
        # Validate crop_mode (only if present)
        if "crop_mode" in settings:
            valid_crops = ["smart_crop", "letterbox", "stretch"]
            if settings.get("crop_mode") not in valid_crops:
                errors["crop_mode"] = f"Must be one of: {', '.join(valid_crops)}"
        
        # Validate transition_effect (only if present)
        if "transition_effect" in settings:
            valid_transitions = ["fade", "slide", "none"]
            if settings.get("transition_effect") not in valid_transitions:
                errors["transition_effect"] = f"Must be one of: {', '.join(valid_transitions)}"
        
        # Update interval removed: scheduling handled externally
        
        return errors
    
    def get_status(self) -> Dict[str, Any]:
        """Get channel status for debugging"""
        all_images = self.metadata.get_all_images()
        image_count = len(all_images)
        enabled_count = len([img for img in all_images if img.get("enabled", True)])
        
        return {
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "last_error": self.last_error,
            "current_image_id": self.current_image_id,
            "total_images": image_count,
            "enabled_images": enabled_count,
            "metadata_system": "file_based_json",
            "storage_usage": self._get_storage_usage()
        }
    
    def get_router(self) -> APIRouter:
        """Return FastAPI router for channel-specific endpoints (hardened).

        Adds defensive try/except so a route construction failure is surfaced
        as a clear log + preserved in self.last_error for manifest diagnostics.
        """
        try:  # noqa: C901 (router assembly verbosity is acceptable here)
            router = APIRouter()

            # Include all route modules with dependency injection
            router.include_router(create_images_router(
                self.image_service, self.gallery_service, self.storage_service,
                self.metadata, self.image_processor
            ))
            router.include_router(create_galleries_router(
                self.gallery_service, self.image_service, self.storage_service
            ))
            router.include_router(create_settings_router(
                self.gallery_service, self.storage_service, self.settings_manager,
                self._config
            ))
            router.include_router(create_subchannel_settings_router(
                self.gallery_service, self.settings_manager
            ))
            router.include_router(create_assets_router(self.storage_service, self.channel_dir))
            router.include_router(create_legacy_assets_router(self.storage_service, self.channel_dir))
            router.include_router(create_admin_router(
                self.image_service, self.gallery_service, self.storage_service,
                self.rendering_service, self.settings_manager, self.metadata
            ))
            # request-image rendering endpoint
            router.include_router(create_render_router(
                self.rendering_service,
                self.gallery_service,
                self.image_service,
                self.channel_dir,
                channel_request_image=self.request_image,
            ))

            # Lightweight feature probe endpoints
            @router.get("/test")
            async def test_get():  # type: ignore
                return JSONResponse({
                    "success": True,
                    "id": self.id,
                    "message": "Photo Frame channel responsive",
                    "supports_subchannels": True,
                    "total_images": len(self.metadata.get_all_images())
                })

            @router.post("/test")
            async def test_post():  # type: ignore
                return JSONResponse({
                    "success": True,
                    "id": self.id,
                    "message": "Photo Frame channel responsive",
                    "supports_subchannels": True,
                    "total_images": len(self.metadata.get_all_images())
                })

            logger.info(
                "[PhotoFrame] Router built subchannels=%d images=%d",
                len(self.get_subchannels()),
                len(self.metadata.get_all_images()),
            )
            return router
        except Exception as e:  # noqa: BLE001
            self.last_error = f"router_build_failed:{e}"
            logger.error("[PhotoFrame] Router build failed: %s", e)
            raise
        
    
    async def _regenerate_all_thumbnails(self):
        """Regenerate thumbnails for all images in the database"""
        from PIL import Image
        
        images = self.metadata.get_all_images()
        thumbnails_dir = self.channel_dir / "data" / "thumbs"
        uploads_dir = self.channel_dir / "assets" / "uploads"
        
        # Ensure thumbnails directory exists
        thumbnails_dir.mkdir(parents=True, exist_ok=True)
        
        count = 0
        for image in images:
            filename = image["filename"]
            source_path = uploads_dir / filename
            thumb_path = thumbnails_dir / filename
            
            if source_path.exists():
                try:
                    # Generate thumbnail
                    with Image.open(source_path) as img:
                        # Create thumbnail (150x150 max, maintaining aspect ratio)
                        thumbnail = img.copy()
                        thumbnail.thumbnail((150, 150), Image.LANCZOS)
                        
                        # Save thumbnail as JPEG
                        if filename.lower().endswith('.png'):
                            # Convert PNG to JPEG for thumbnails
                            thumbnail = thumbnail.convert('RGB')
                        
                        thumbnail.save(thumb_path, "JPEG", quality=85)
                        count += 1
                        print(f"Generated thumbnail for {filename}")
                except Exception as e:
                    print(f"Failed to generate thumbnail for {filename}: {e}")
        
        return count
    
    async def _rebuild_database_from_files(self):
        """Rebuild database from existing files in uploads directory"""
        from PIL import Image
        import os
        
        uploads_dir = self.channel_dir / "assets" / "uploads"
        count = 0
        
        if not uploads_dir.exists():
            return 0
        
        # Get all image files from uploads directory
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        
        for file_path in uploads_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                try:
                    # Check if image already exists in metadata
                    existing = self.metadata.get_image_by_filename(file_path.name)
                    if existing:
                        print(f"Image {file_path.name} already exists in metadata, skipping")
                        continue
                    
                    # Get image dimensions
                    with Image.open(file_path) as img:
                        width, height = img.size
                    
                    # Add to file metadata system
                    image_data = {
                        "filename": file_path.name,
                        "original_name": file_path.name,
                        "width": width,
                        "height": height
                    }
                    
                    self.metadata.add_image(image_data)
                    count += 1
                    print(f"Added image {file_path.name} to file metadata system")
                    
                except Exception as e:
                    print(f"Failed to process {file_path.name}: {e}")
        
        return count

    async def _regenerate_colocated_thumbnails(self):
        """Regenerate thumbnails using the new co-located approach"""
        try:
            from PIL import Image
        except ImportError:
            raise HTTPException(status_code=500, detail="PIL not available for thumbnail generation")
        
        all_images = self.metadata.get_all_images()
        uploads_dir = self.channel_dir / "assets" / "uploads"
        
        generated_count = 0
        error_count = 0
        errors = []
        
        for image in all_images:
            filename = image["filename"]
            source_path = uploads_dir / filename
            
            # Generate thumbnail filename: image.jpg -> image.thumb.jpg
            name_stem = Path(filename).stem
            thumb_filename = f"{name_stem}.thumb.jpg"
            thumb_path = uploads_dir / thumb_filename
            
            if source_path.exists():
                try:
                    # Generate thumbnail
                    with Image.open(source_path) as img:
                        # Convert to RGB if necessary (for PNG with transparency)
                        if img.mode in ('RGBA', 'LA', 'P'):
                            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                            rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                            img = rgb_img
                        
                        # Create thumbnail
                        img.thumbnail((600, 600), Image.Resampling.LANCZOS)
                        img.save(thumb_path, "JPEG", quality=85, optimize=True)
                        
                        generated_count += 1
                        print(f"Generated thumbnail: {thumb_filename}")
                        
                except Exception as e:
                    error_count += 1
                    error_msg = f"Failed to generate thumbnail for {filename}: {str(e)}"
                    errors.append(error_msg)
                    print(error_msg)
            else:
                error_count += 1
                error_msg = f"Source image not found: {filename}"
                errors.append(error_msg)
                print(error_msg)
        
        return {
            "total_images": len(all_images),
            "generated_count": generated_count,
            "error_count": error_count,
            "errors": errors
        }
    

    
    async def _process_placeholder_for_display(
        self, 
        placeholder_path: Path, 
        output_path: Path, 
        resolution: tuple, 
        settings: dict
    ):
        """Process placeholder image for display"""
        # Create a mock image record for placeholder processing
        placeholder_record = {
            "filename": "placeholder.jpg",
            "crop_x": 0,
            "crop_y": 0,
            "crop_width": 100,
            "crop_height": 100
        }
        
        # Use aspect-safe processing logic
        crop_mode = self._canonicalize_crop_mode(settings.get("crop_mode"))
        if crop_mode in ("opencv-saliency",):
            if hasattr(self.image_processor, "process_opencv_saliency"):
                await self.image_processor.process_opencv_saliency(
                    placeholder_path,
                    output_path,
                    resolution,
                    placeholder_record,
                    settings,
                )
            else:
                await self.image_processor.process_smart_crop(
                    placeholder_path,
                    output_path,
                    resolution,
                    placeholder_record,
                )
        elif crop_mode == "letterbox":
            await self.image_processor.process_letterbox(
                placeholder_path,
                output_path,
                resolution,
            )
        elif crop_mode == "stretch":
            await self.image_processor.process_stretch(
                placeholder_path,
                output_path,
                resolution,
            )
        else:
            await self.image_processor.process_smart_crop(
                placeholder_path,
                output_path,
                resolution,
                placeholder_record,
            )
    
    async def _process_image_for_display(
        self, 
        image_record: Dict[str, Any], 
        resolution: Tuple[int, int], 
        orientation: str,
        settings: Dict[str, Any]
    ) -> str:
        """Process image according to crop settings and display mode"""
        
        source_path = self.channel_dir / "assets" / "uploads" / image_record["filename"]
        output_path = self.channel_dir / self.config["current_image"]
        
        crop_mode = self._canonicalize_crop_mode(settings.get("crop_mode"))

        if crop_mode in ("opencv-saliency",):
            if hasattr(self.image_processor, "process_opencv_saliency"):
                await self.image_processor.process_opencv_saliency(
                    source_path,
                    output_path,
                    resolution,
                    image_record,
                    settings,
                )
            else:
                await self.image_processor.process_smart_crop(
                    source_path,
                    output_path,
                    resolution,
                    image_record,
                )
        elif crop_mode == "letterbox":
            await self.image_processor.process_letterbox(
                source_path,
                output_path,
                resolution,
            )
        elif crop_mode == "stretch":
            await self.image_processor.process_stretch(
                source_path,
                output_path,
                resolution,
            )
        else:  # smart_crop default
            await self.image_processor.process_smart_crop(
                source_path,
                output_path,
                resolution,
                image_record,
            )
        
        return str(output_path)
    
    async def _update_image_stats(self, image_id: str):
        """Update image display statistics"""
        image = self.metadata.get_image_by_id(image_id)
        if image:
            self.metadata.update_image(image_id, {
                "times_shown": image.get("times_shown", 0) + 1,
                "last_shown_at": datetime.now(timezone.utc).isoformat()
            })
    
    def _get_storage_usage(self) -> Dict[str, Any]:
        """Calculate storage usage"""
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
        """Get fallback image when primary rendering fails"""
        
        # Try last successful image
        if self.current_image_id and os.path.exists(self.config["current_image"]):
            return self.config["current_image"]
        
        # Try any enabled image
        all_images = self.metadata.get_all_images()
        enabled_images = [img for img in all_images if img.get("enabled", True)]
        if enabled_images:
            return await self._render_simple_fallback(enabled_images[0])
        
        # Use placeholder
        return self.config["placeholder_image"]
    
    async def _render_simple_fallback(self, image_record):
        """Render a simple fallback version of an image"""
        # Simple implementation for fallback
        return self.config["placeholder_image"]
    
    # =============================================================================
    # Gallery (Sub-Channel) Support Methods - Delegated to GalleryService
    # =============================================================================
    
    def supports_subchannels(self) -> bool:
        """Returns True - this channel supports galleries"""
        return True
    
    def get_subchannel_config(self) -> Dict[str, Any]:
        """Get sub-channel configuration"""
        return {
            "enabled": True,
            "label": "Gallery",
            "labelPlural": "Galleries",
            "description": "Organize photos into themed collections",
            "supports_tagging": True,
            "supports_multiple_membership": True,
            "allowCustom": True,
            "contentType": "image",
            "maxSubChannels": 50,
            "examples": [
                {"name": "Family Photos", "description": "Pictures of family members"},
                {"name": "Vacation 2024", "description": "Travel photos from this year"},
                {"name": "Nature", "description": "Landscape and wildlife photography"},
                {"name": "Portraits", "description": "Professional and casual portraits"}
            ]
        }
    
    def list_subchannels(self) -> List[Dict[str, Any]]:
        """Get all galleries - API-compatible method name"""
        return [gallery.to_dict() for gallery in self.gallery_service.get_all_galleries()]
    
    def get_subchannels(self) -> List[Dict[str, Any]]:
        """Get all galleries by delegating to the GalleryService"""
        return [gallery.to_dict() for gallery in self.gallery_service.get_all_galleries()]
    
    def create_subchannel(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new gallery by delegating to the GalleryService"""
        gallery_create = GalleryCreate(**data)
        gallery = self.gallery_service.create_gallery(gallery_create)
        return {"success": True, "subchannel": gallery.to_dict()}
    
    def get_subchannel(self, subchannel_id: str) -> Dict[str, Any]:
        """Get specific subchannel details - API-compatible method"""
        gallery = self.gallery_service.get_gallery(subchannel_id)
        if not gallery:
            return None
        return gallery.to_dict()
    
    def update_subchannel(self, subchannel_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a gallery by delegating to the GalleryService"""
        gallery_update = GalleryUpdate(**data)
        gallery = self.gallery_service.update_gallery(subchannel_id, gallery_update)
        return {"success": True, "gallery": gallery.to_dict()}
    
    def delete_subchannel(self, subchannel_id: str) -> Dict[str, Any]:
        """Delete a gallery by delegating to the GalleryService"""
        # Get gallery info before deletion for response
        gallery = self.gallery_service.get_gallery(subchannel_id)
        if not gallery:
            return {"success": False, "error": "Gallery not found"}
        
        gallery_info = gallery.to_dict()
        success = self.gallery_service.delete_gallery(subchannel_id)
        
        if success:
            return {
                "success": True,
                "message": f"Subchannel '{gallery_info.get('name', subchannel_id)}' has been deleted",
                "deletedSubchannel": {
                    "id": gallery_info["id"],
                    "name": gallery_info.get("name", ""),
                    "imageCount": gallery_info.get("imageCount", 0)
                }
            }
        else:
            return {"success": False, "error": "Failed to delete gallery"}
    
    def assign_content_to_subchannel(
        self, 
        subchannel_id: str, 
        content_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assign images to a gallery - API-compatible method"""
        content_ids = content_data.get('contentIds', [])
        action = content_data.get('action', 'add')
        
        if not content_ids:
            return {"success": False, "error": "No content IDs provided"}
        
        if action not in ['add', 'remove']:
            return {"success": False, "error": "Action must be 'add' or 'remove'"}
        
        # Get all available image IDs
        all_image_ids = {str(img["id"]) for img in self.metadata.get_all_images()}
        
        # Perform the assignment
        success = self.gallery_service.assign_images_to_gallery(
            subchannel_id, content_ids, action, all_image_ids
        )
        
        if success:
            # Return updated gallery information
            gallery = self.gallery_service.get_gallery(subchannel_id)
            return {"success": True, "gallery": gallery.to_dict() if gallery else None}
        else:
            return {"success": False, "error": "Failed to assign content to gallery"}
    
    def get_subchannel_content(
        self, 
        subchannel_id: str, 
        limit: int = None, 
        offset: int = None
    ) -> Dict[str, Any]:
        """Get gallery content by delegating to the GalleryService"""
        all_images = self.metadata.get_all_images()
        return self.gallery_service.get_gallery_content(
            subchannel_id, all_images, limit, offset
        )
    
    def list_subchannel_images(
        self, 
        subchannel_id: str, 
        include_metadata: bool = False
    ) -> Dict[str, Any]:
        """Get list of images in a specific subchannel - API-compatible method"""
        gallery = self.gallery_service.get_gallery(subchannel_id)
        if not gallery:
            return {"error": "Subchannel not found"}
        
        all_images = self.metadata.get_all_images()
        gallery_content = self.gallery_service.get_gallery_content(
            subchannel_id, all_images
        )
        
        if not include_metadata:
            # Return just the basic list
            return {
                "images": [{"id": img["id"]} for img in gallery_content.get("images", [])],
                "total": gallery_content.get("total", 0),
                "subchannel": {
                    "id": gallery.id,
                    "name": gallery.name,
                    "imageCount": len(gallery.content_ids)
                }
            }
        else:
            # Return full metadata
            return {
                "images": gallery_content.get("images", []),
                "total": gallery_content.get("total", 0),
                "subchannel": {
                    "id": gallery.id,
                    "name": gallery.name,
                    "description": gallery.description,
                    "imageCount": len(gallery.content_ids),
                    "created": gallery.created,
                    "modified": gallery.modified
                }
            }
    
    def get_subchannel_image_thumbnail(
        self, 
        subchannel_id: str, 
        image_id: str
    ) -> Optional[str]:
        """Get thumbnail path for a specific image within a subchannel"""
        # First verify the image belongs to the subchannel
        gallery = self.gallery_service.get_gallery(subchannel_id)
        if not gallery:
            return None
        
        if str(image_id) not in gallery.content_ids:
            return None
        
        # Try to get thumbnail from image service
        uploads_dir = self.channel_dir / "assets" / "uploads"
        
        # Try various thumbnail naming patterns
        thumbnail_patterns = [
            f"image_{image_id}.thumb.jpg",
            f"thumb_{image_id}.jpg",
            f"{image_id}.thumb.jpg",
            f"image_{image_id}_thumb.jpg"
        ]
        
        for pattern in thumbnail_patterns:
            thumbnail_path = uploads_dir / pattern
            if thumbnail_path.exists():
                return str(thumbnail_path)
        
        # Fallback to original image
        image_patterns = [
            f"image_{image_id}.jpg",
            f"image_{image_id}.png",
            f"image_{image_id}.jpeg",
            f"{image_id}.jpg",
            f"{image_id}.png"
        ]
        
        for pattern in image_patterns:
            image_path = uploads_dir / pattern
            if image_path.exists():
                return str(image_path)
        
        return None
    
    def get_subchannel_settings(self, subchannel_id: str) -> Dict[str, Any]:
        """Get subchannel-specific settings - API-compatible method"""
        try:
            return self.gallery_service.get_gallery_settings(subchannel_id)
        except ValueError:
            # Gallery not found, return default settings
            return {
                "order_mode": {"value": "added"},
                "crop_mode": {"value": "smart_crop"},
                "slideshow_enabled": {"value": True},
                "transition_effect": {"value": "fade"}
            }
    
    def update_subchannel_settings(
        self, 
        subchannel_id: str, 
        settings_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update subchannel-specific settings - API-compatible method"""
        try:
            # Update settings through gallery service
            self.gallery_service.update_gallery_settings(subchannel_id, settings_data)
            return {"success": True, "settings": settings_data}
        except ValueError as e:
            return {"success": False, "error": str(e)}
    
    # =============================================================================
    # Image Management Methods - API-Compatible
    # =============================================================================
    
    def list_images(self) -> List[Dict[str, Any]]:
        """Get list of all images - API-compatible method"""
        return self.metadata.get_all_images()
    
    async def upload_images(
        self, 
        files: List[UploadFile]
    ) -> Dict[str, Any]:
        """Upload images to the channel - API-compatible method"""
        import hashlib
        import time
        from pathlib import Path
        
        # Use the root uploads directory for generic API uploads
        uploads_dir = self.channel_dir / "assets" / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        results = []
        
        for file in files:
            # Validate file type
            if not file.content_type or not file.content_type.startswith('image/'):
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": "File is not an image"
                })
                continue
            
            try:
                # Read file content asynchronously
                content = await file.read()
                if len(content) == 0:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": "Empty file"
                    })
                    continue
                
                # Generate unique filename
                timestamp = str(int(time.time() * 1000))
                content_hash = hashlib.md5(content + timestamp.encode()).hexdigest()[:12]
                
                # Preserve original extension, default to jpg
                original_ext = Path(file.filename).suffix.lower() if file.filename else ''
                if not original_ext or original_ext not in ['.jpg', '.jpeg', '.png', '.gif']:
                    original_ext = '.jpg'
                
                new_filename = f"image_{content_hash}{original_ext}"
                file_path = uploads_dir / new_filename
                
                # Save original file
                with open(file_path, 'wb') as f:
                    f.write(content)
                
                # Generate co-located thumbnail
                thumbnail_filename = f"image_{content_hash}.thumb.jpg"
                thumbnail_path = uploads_dir / thumbnail_filename
                
                try:
                    from PIL import Image
                    
                    with Image.open(file_path) as img:
                        # Convert to RGB if necessary
                        if img.mode in ('RGBA', 'LA', 'P'):
                            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                            if img.mode in ('RGBA', 'LA'):
                                rgb_img.paste(img, mask=img.split()[-1])
                            else:
                                rgb_img.paste(img)
                            img = rgb_img
                        
                        # Create thumbnail
                        img.thumbnail((600, 600), Image.Resampling.LANCZOS)
                        img.save(thumbnail_path, 'JPEG', quality=85, optimize=True)
                        
                except ImportError:
                    pass  # PIL not available
                except Exception:
                    pass  # Thumbnail generation failed
                
                # Add to metadata system
                image_data = {
                    "filename": new_filename,
                    "original_name": file.filename
                }
                
                # Get dimensions if possible
                try:
                    from PIL import Image
                    with Image.open(file_path) as img:
                        image_data["width"], image_data["height"] = img.size
                except:
                    image_data["width"] = 1920
                    image_data["height"] = 1080
                
                image_record = self.metadata.add_image(image_data)
                
                results.append({
                    "filename": new_filename,
                    "original_name": file.filename,
                    "success": True,
                    "image_id": image_record["id"],
                    "thumbnail": thumbnail_filename if thumbnail_path.exists() else None,
                    "file_size": len(content)
                })
                
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": str(e)
                })
        
        return {"results": results}
    
    def delete_image(self, image_id: str) -> Dict[str, Any]:
        """Delete an image from the channel - API-compatible method"""
        try:
            # Get image info before deletion
            image = self.metadata.get_image_by_id(image_id)
            if not image:
                return {"success": False, "error": "Image not found"}
            
            # Remove from filesystem
            uploads_dir = self.channel_dir / "assets" / "uploads"
            image_path = uploads_dir / image["filename"]
            
            if image_path.exists():
                image_path.unlink()
            
            # Remove thumbnail if it exists
            thumbnail_patterns = [
                f"image_{image_id}.thumb.jpg",
                f"thumb_{image_id}.jpg",
                f"{image_id}.thumb.jpg"
            ]
            
            for pattern in thumbnail_patterns:
                thumb_path = uploads_dir / pattern
                if thumb_path.exists():
                    thumb_path.unlink()
                    break
            
            # Remove from metadata
            self.metadata.delete_image(image_id)
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def reorder_gallery_images(self, gallery_id: str, dragged_id: str, target_id: str) -> bool:
        """Reorder images in a gallery by delegating to the GalleryService"""
        return self.gallery_service.reorder_gallery_images(gallery_id, dragged_id, target_id)

    # =========================================================================
    # Embedded Plugin Interface - Required for Mimir Plugin Architecture
    # =========================================================================
    
    def get_manifest(self) -> Dict[str, Any]:
        """Return channel manifest with health + diagnostics for platform discovery."""
        try:  # noqa: C901
            galleries = self.gallery_service.get_all_galleries()
            healthy = self.last_error is None
            manifest = {
                "id": "com.epaperframe.photoframe",
                "name": "Photo Frame Channel",
                "version": "1.0.0",
                "description": "Gallery-based photo slideshow with intelligent image management",
                "capabilities": {
                    "supports_upload": True,
                    "supports_gallery": True,
                    "supports_randomization": True,
                    "image_formats": ["jpg", "jpeg", "png", "gif"],
                    "max_file_size": "10MB"
                },
                "ui": {
                    "entry_point": "/api/channels/com.epaperframe.photoframe/ui/index.html",
                    "components": {
                        "manager": "/api/channels/com.epaperframe.photoframe/ui/manage.esm.js",
                        "gallery_card": "/api/channels/com.epaperframe.photoframe/ui/components/gallery-card.js",
                        "image_card": "/api/channels/com.epaperframe.photoframe/ui/components/image-card.js"
                    },
                    "styles": "/api/channels/com.epaperframe.photoframe/ui/styles.css",
                    "icon": "🖼️",
                    "title": "Photo Frame Manager",
                    "elements": {
                        "manager": "x-photo-frame-manager",
                        "gallery_card": "photo-frame-gallery-card",
                        "image_card": "photo-frame-image-card"
                    }
                },
                "galleries": [
                    {"id": g.id, "name": g.name, "image_count": g.image_count} for g in galleries
                ],
                "status": self.get_status(),
                "healthy": healthy,
                "diagnostics": {
                    "last_error": self.last_error,
                    "image_count": len(self.metadata.get_all_images()),
                    "cache_entries": len(self._render_cache),
                    "last_update": self.last_update.isoformat() if self.last_update else None,
                },
            }
            logger.info(
                "[PhotoFrame] Manifest served healthy=%s galleries=%d images=%d cache=%d",  # noqa: G004
                healthy,
                len(galleries),
                len(self.metadata.get_all_images()),
                len(self._render_cache),
            )
            return manifest
        except Exception as e:  # noqa: BLE001
            logger.error("[PhotoFrame] Manifest generation failed: %s", e)
            return {
                "id": "com.epaperframe.photoframe",
                "name": "Photo Frame Channel",
                "healthy": False,
                "error": str(e),
                "diagnostics": {"last_error": str(e)},
            }
    
    async def request_image(self, request_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Return processed image with modern transport contract.

        Modern contract (for central API router):
          - Always provide raw bytes in 'bytes'
          - Provide 'content_type' (default image/jpeg, sniffed if PNG)
          - ONLY provide base64 (legacy) when include_base64=true in request_data
          - Preserve prior metadata fields for backward compatibility

        This enables the platform to store the image in the in-memory channel_image_store
        and expose it via /api/channels/{channel_id}/images/{image_id} without forcing
        base64 transfer overhead.
        """
        try:  # noqa: C901 (complex but self-contained)
            data = request_data or {}
            include_base64 = bool(data.get("include_base64"))
            # Optional explicit suppression (mirrors spotify channel pattern)
            suppress_legacy_base64 = bool(data.get("suppress_legacy_base64"))

            gallery_id = data.get("gallery_id")
            settings_raw = data.get("settings", {})
            # Normalize incoming settings
            settings_norm = self._normalize_settings(settings_raw)
            # If a gallery is specified, merge its saved settings (caller overrides gallery)
            if gallery_id:
                try:
                    gallery_saved = self.gallery_service.get_gallery_settings(gallery_id)
                except Exception:  # noqa: BLE001
                    gallery_saved = {}
                gallery_norm = self._normalize_settings(gallery_saved or {})
                # Caller-provided settings take precedence over gallery defaults
                tmp = dict(gallery_norm)
                tmp.update(settings_norm)
                settings_norm = tmp

            distribution_mode = settings_norm.get("distribution", "new")
            if distribution_mode not in ("current", "new"):
                distribution_mode = "new"

            # Resolution parsing with defensive fallbacks
            resolution = settings_norm.get("resolution") or [800, 600]
            if not isinstance(resolution, (list, tuple)) or len(resolution) != 2:
                resolution = [800, 600]
            try:
                width, height = int(resolution[0]), int(resolution[1])
            except Exception:  # noqa: BLE001
                width, height = 800, 600
            if width <= 0 or height <= 0:
                width, height = 800, 600

            # Orientation normalization
            orientation = settings_norm.get("orientation")
            if orientation not in ("landscape", "portrait", "square"):
                orientation = "square" if width == height else ("portrait" if height > width else "landscape")
            if orientation == "square" and width != height:
                side = min(width, height)
                width = height = side

            crop_mode = self._canonicalize_crop_mode(settings_norm.get("crop_mode"))
            gallery_key = gallery_id or "default"
            cache_key = self._render_cache_key(gallery_key, width, height, orientation, crop_mode)

            # Cache reuse (distribution_mode == current)
            if distribution_mode == "current":
                cache_entry = self._render_cache.get(cache_key)
                if cache_entry and (time.time() - cache_entry["ts"]) < self._cache_ttl_seconds:
                    cached_path = cache_entry["path"]
                    if os.path.exists(cached_path):
                        if cache_entry.get("image_id"):
                            self._last_selected_by_gallery[gallery_key] = cache_entry.get("image_id")
                        with open(cached_path, "rb") as f:
                            content_bytes = f.read()
                        # Sniff content type (currently renders JPEG, but future-proof)
                        content_type = "image/jpeg"
                        if content_bytes.startswith(b"\x89PNG"):
                            content_type = "image/png"
                        elif content_bytes[0:2] == b"\xff\xd8":
                            content_type = "image/jpeg"
                        response: Dict[str, Any] = {
                            "success": True,
                            "bytes": content_bytes,
                            "content_type": content_type,
                            "filename": Path(cached_path).name,
                            "image_id": cache_entry.get("image_id"),
                            "gallery_id": gallery_id,
                            "width": width,
                            "height": height,
                            "orientation": orientation,
                            "crop_mode": crop_mode,
                            "distribution_mode": distribution_mode,
                            "cached": True,
                            "message": "Reused cached render",
                            "preferred_transport": "bytes",
                        }
                        if include_base64 and not suppress_legacy_base64:
                            response["image"] = base64.b64encode(content_bytes).decode("utf-8")
                        return response

            # Candidate image gathering
            if gallery_id:
                all_images = self.metadata.get_all_images()
                gallery_content = self.gallery_service.get_gallery_content(gallery_id, all_images)
                images = gallery_content.get("content", []) if gallery_content else []
                gallery_obj = self.gallery_service.get_gallery(gallery_id)
            else:
                images = self.metadata.get_all_images()
                gallery_obj = None
            if not images:
                return {"success": False, "error": "No images available"}
            print(f"[PhotoFrameChannel] candidates gallery={gallery_key} count={len(images)} order_mode={settings_norm.get('order_mode')} distribution={distribution_mode}")

            order_mode = settings_norm.get("order_mode", "added")
            if order_mode not in ("added", "random", "custom"):
                order_mode = "added"

            if order_mode == "random":
                ordered_images = images
            elif order_mode == "custom" and gallery_obj:
                id_to_image = {str(img.get("id")): img for img in images}
                ordered_images = [id_to_image[cid] for cid in gallery_obj.content_ids if cid in id_to_image]
                if not ordered_images:
                    ordered_images = list(images)
                missing_ids = [cid for cid in gallery_obj.content_ids if cid not in id_to_image]
                if missing_ids:
                    try:
                        existing_ids = {str(i.get("id")) for i in all_images}
                        self.gallery_service.validate_galleries_data_integrity(existing_ids)
                        refreshed = self.gallery_service.get_gallery(gallery_id)
                        if refreshed and refreshed is not gallery_obj:
                            gallery_obj = refreshed
                    except Exception:  # noqa: BLE001
                        pass
            else:
                ordered_images = self._get_sorted_images(images, order_mode)
            for img in ordered_images:
                if 'id' in img:
                    img['id'] = str(img['id'])

            selected_image = None
            if order_mode == "random":
                if distribution_mode == "current":
                    last_id = self._last_selected_by_gallery.get(gallery_key)
                    if last_id:
                        for img in images:
                            if img.get("id") == last_id:
                                selected_image = img
                                break
                if not selected_image:
                    selected_image = self._select_image_by_distribution(images, "new", gallery_key)
            else:
                if distribution_mode == "current":
                    last_id = self._last_selected_by_gallery.get(gallery_key)
                    if last_id:
                        for img in ordered_images:
                            if img.get("id") == last_id:
                                selected_image = img
                                break
                if not selected_image:
                    selected_image = self._next_sequential_image(ordered_images, gallery_key)
            if not selected_image:
                return {"success": False, "error": "Unable to select image"}
            print(f"[PhotoFrameChannel] selected image_id={selected_image.get('id')} gallery={gallery_key} mode={order_mode} dist={distribution_mode}")

            merged_settings = dict(settings_norm)
            merged_settings["crop_mode"] = crop_mode
            rendered_path = await self._render_selected_image(
                selected_image,
                (width, height),
                orientation=orientation,
                settings=merged_settings,
                gallery_id=gallery_id,
            )
            if not rendered_path or not os.path.exists(rendered_path):
                return {"success": False, "error": "Render failed"}

            with open(rendered_path, "rb") as f:
                content_bytes = f.read()

            content_type = "image/jpeg"
            if content_bytes.startswith(b"\x89PNG"):
                content_type = "image/png"
            elif content_bytes[0:2] == b"\xff\xd8":
                content_type = "image/jpeg"

            # Update caches
            self._last_selected_by_gallery[gallery_key] = selected_image.get("id")
            self._render_cache[cache_key] = {
                "path": rendered_path,
                "image_id": selected_image.get("id"),
                "ts": time.time(),
            }

            response: Dict[str, Any] = {
                "success": True,
                "bytes": content_bytes,
                "content_type": content_type,
                "filename": Path(rendered_path).name,
                "image_id": selected_image.get("id"),
                "gallery_id": gallery_id,
                "width": width,
                "height": height,
                "orientation": orientation,
                "crop_mode": crop_mode,
                "distribution_mode": distribution_mode,
                "cached": False,
                "message": "Rendered new image",
                "preferred_transport": "bytes",
            }
            if include_base64 and not suppress_legacy_base64:
                response["image"] = base64.b64encode(content_bytes).decode("utf-8")
            return response
        except Exception as e:  # noqa: BLE001
            return {"success": False, "error": f"Image request failed: {e}"}

    async def _render_selected_image(
        self,
        image_record: Dict[str, Any],
        resolution: Tuple[int, int],
        orientation: str,
        settings: Dict[str, Any],
        gallery_id: Optional[str] = None,
    ) -> Optional[str]:
        """Render a specific pre-selected image to the resolution-specific cache path.

        This isolates rendering from selection so request_image's ordering logic is
        honored. Mirrors parts of render_image() without picking a new image.
        """
        try:
            width, height = resolution
            resolution_folder = f"{width}x{height}"
            resolution_dir = self.channel_dir / "current" / resolution_folder
            resolution_dir.mkdir(parents=True, exist_ok=True)
            output_path = resolution_dir / "current.jpg"

            await self._process_image_for_display(
                image_record,
                resolution,
                orientation,
                settings,
            )
            legacy_current = self.channel_dir / self.config["current_image"]
            if legacy_current.exists():
                shutil.copy2(legacy_current, output_path)
            await self._update_image_stats(image_record.get("id"))
            self.current_image_id = image_record.get("id")
            self.last_update = datetime.now(timezone.utc)
            self.last_error = None
            return str(output_path)
        except Exception as e:  # noqa: BLE001
            self.last_error = str(e)
            return None

    # Helper utilities
    def _normalize_settings(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        norm: Dict[str, Any] = {}
        for k, v in raw.items():
            if isinstance(v, dict) and set(v.keys()) == {"value"}:
                norm[k] = v["value"]
            else:
                norm[k] = v
        return norm

    def _canonicalize_crop_mode(self, value: Optional[str]) -> str:
        if not value:
            return "smart_crop"
        v = str(value).lower().replace("-", "_")
        # Fit -> pad/letterbox (no distortion)
        if v in ("fit", "fit_to_screen", "letterbox", "fit_screen"):
            return "letterbox"
        # Fill/Cover should be a content-preserving crop (smart_crop), NOT stretch
        if v in ("fill", "fill_screen", "cover"):
            return "smart_crop"
        # OpenCV saliency mode canonicalization
        if v in ("opencv_saliency", "opencv", "saliency"):
            return "opencv-saliency"
        # Only allow these internal modes
        if v not in ("smart_crop", "letterbox", "stretch", "opencv-saliency"):
            return "smart_crop"
        return v

    def _render_cache_key(self, gallery_key: str, width: int, height: int, orientation: str, crop_mode: str) -> str:
        return f"{gallery_key}:{width}x{height}:{orientation}:{crop_mode}"

    def _select_image_by_distribution(self, images: List[Dict[str, Any]], distribution_mode: str, gallery_key: str) -> Optional[Dict[str, Any]]:
        if not images:
            return None
        # Order mode aware rotation will be handled elsewhere; here we just avoid repeat for random fallback
        last_id = self._last_selected_by_gallery.get(gallery_key)
        candidates = [img for img in images if img.get("id") != last_id] or images
        return random.choice(candidates)

    # --- New order-aware helpers -------------------------------------------------
    def _get_sorted_images(self, images: List[Dict[str, Any]], order_mode: str) -> List[Dict[str, Any]]:
        """Return images ordered for non-custom persisted modes.

        Custom ordering now relies directly on gallery.content_ids inside request_image;
        this helper retains legacy behavior for 'added' (insertion order) and any future
        simple strategies. We keep a defensive branch for 'custom' but it will normally
        be bypassed by earlier logic.
        """
        if order_mode == "added":
            return list(images)
        if order_mode == "custom":  # defensive fallback (should be handled earlier)
            return sorted(images, key=lambda i: i.get("position", 1_000_000))
        # random handled during selection
        return list(images)

    def _next_sequential_image(self, images: List[Dict[str, Any]], gallery_key: str) -> Optional[Dict[str, Any]]:
        """Return next image in sequence.

        Uses in-memory last selection when available; otherwise falls back to a
        persisted heuristic based on times_shown and last_shown_at so rotation
        still progresses even if the channel instance was recreated.
        """
        if not images:
            return None
        last_id = self._last_selected_by_gallery.get(gallery_key)
        if last_id:
            for idx, img in enumerate(images):
                if str(img.get("id")) == str(last_id):
                    return images[(idx + 1) % len(images)]
        # Stateless fallback: pick the least shown image; tie-break on last_shown_at then original order
        scored: list[tuple[int, str, int, Dict[str, Any]]] = []
        for idx, img in enumerate(images):
            times = img.get("times_shown", 0) or 0
            # None should sort before later timestamps so use '': empty string sorts first
            last_shown = img.get("last_shown_at") or ""
            scored.append((times, last_shown, idx, img))
        scored.sort(key=lambda t: (t[0], t[1], t[2]))
        return scored[0][3] if scored else None

# Export the channel class for embedded plugin discovery
ChannelClass = PhotoFrameChannel
