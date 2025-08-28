import os
import sys
import json
import asyncio
import re
import random
import shutil
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
from pathlib import Path
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse

# New model imports
try:
    from models import (
        Gallery, GalleryCreate, GalleryUpdate,
        Image, ImageMetadata, ImageUploadResult, ImageBatchUploadResult,
        ChannelSettings, GallerySettings, SettingsManager
    )
except ImportError:
    # Fallback for when running from channel directory
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from models import (
        Gallery, GalleryCreate, GalleryUpdate,
        Image, ImageMetadata, ImageUploadResult, ImageBatchUploadResult,
        ChannelSettings, GallerySettings, SettingsManager
    )

# New service imports  
try:
    from services import (
        GalleryService, ImageService, RenderingService, StorageService
    )
except ImportError:
    # Fallback for when running from channel directory
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from services import (
        GalleryService, ImageService, RenderingService, StorageService
    )

# New route imports
try:
    from routes import (
        create_images_router, create_galleries_router, create_settings_router,
        create_assets_router, create_legacy_assets_router, create_admin_router,
        create_subchannel_settings_router
    )
except ImportError:
    # Fallback for when running from channel directory
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from routes import (
        create_images_router, create_galleries_router, create_settings_router,
        create_assets_router, create_legacy_assets_router, create_admin_router,
        create_subchannel_settings_router
    )

# Handle imports for both standalone and platform usage
try:
    from utils.image_processor import ImageProcessor
    from utils.file_metadata import FileMetadataManager
except ImportError:
    # Fallback for standalone testing
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from utils.image_processor import ImageProcessor
    from utils.file_metadata import FileMetadataManager

# BaseChannel interface for Mimir Platform integration
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
        
        # NEW: Initialize services for improved architecture
        self.settings_manager = SettingsManager()  # Add missing settings manager
        self.gallery_service = GalleryService(self.channel_dir)
        self.image_service = ImageService(
            self.channel_dir, 
            self.metadata,
            self.image_processor
        )
        self.rendering_service = RenderingService(self.channel_dir)
        self.storage_service = StorageService(self.channel_dir)
        
        # Ensure directories exist
        self._ensure_directories()
        
        print(f"✅ Photo Frame Channel initialized:")
        print(f"   📂 Channel Directory: {self.channel_dir}")
        print(f"   🆔 Channel ID: {self.id}")
        print(f"   📡 API Base: /api/channels/{self.id}/")
    
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
        
        # Check critical directories
        required_dirs = [
            self.channel_dir / "assets" / "uploads",
            self.channel_dir / "data"
        ]
        
        for dir_path in required_dirs:
            if not dir_path.exists():
                print(f"📁 Creating required directory: {dir_path}")
                dir_path.mkdir(parents=True, exist_ok=True)
    
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
        
        # Validate update_interval_unit (only if present)
        if "update_interval_unit" in settings:
            valid_units = ["days", "hours", "minutes", "seconds"]
            if settings.get("update_interval_unit") not in valid_units:
                errors["update_interval_unit"] = f"Must be one of: {', '.join(valid_units)}"
        
        # Validate update_interval_value (only if present)
        if "update_interval_value" in settings:
            try:
                value = int(settings.get("update_interval_value"))
                if value < 1:
                    errors["update_interval_value"] = "Must be at least 1"
            except (TypeError, ValueError):
                errors["update_interval_value"] = "Must be a valid positive integer"
        
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
        """Return FastAPI router for channel-specific endpoints"""
        router = APIRouter()
        
        # NEW ROUTES ARCHITECTURE - ACTIVATED!
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
        
        return router
        
    
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
        
        # Use existing processing logic but with placeholder
        crop_mode = settings.get("crop_mode", "smart_crop")
        
        if crop_mode == "smart_crop":
            await self.image_processor.render_with_crop(
                source_path=placeholder_path,
                output_path=output_path,
                resolution=resolution,
                crop_x=0,
                crop_y=0,
                crop_width=100,
                crop_height=100
            )
        elif crop_mode == "letterbox":
            await self.image_processor.render_letterbox(
                source_path=placeholder_path,
                output_path=output_path,
                resolution=resolution
            )
        else:  # "stretch"
            await self.image_processor.render_stretch(
                source_path=placeholder_path,
                output_path=output_path,
                resolution=resolution
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
        
        crop_mode = settings.get("crop_mode", "smart_crop")
        
        if crop_mode == "smart_crop":
            # Use stored crop coordinates
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
            # Preserve aspect ratio with borders
            await self.image_processor.render_letterbox(
                source_path=source_path,
                output_path=output_path,
                resolution=resolution
            )
        else:  # "stretch"
            # Stretch to fill (may distort)
            await self.image_processor.render_stretch(
                source_path=source_path,
                output_path=output_path,
                resolution=resolution
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
                "update_interval_value": {"value": 30},
                "update_interval_unit": {"value": "minutes"},
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
    
    def upload_images(
        self, 
        files: List[UploadFile], 
        gallery_id: str = None
    ) -> Dict[str, Any]:
        """Upload images to the channel - API-compatible method"""
        import asyncio
        import hashlib
        import time
        from pathlib import Path
        
        # Determine upload directory based on gallery_id
        if gallery_id:
            uploads_dir = self.channel_dir / "assets" / "uploads" / gallery_id
        else:
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
                # Read file content synchronously since we're not in an async context
                content = asyncio.run(file.read()) if hasattr(file, 'read') else file.file.read()
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
                    "original_name": file.filename,
                    "gallery_id": gallery_id
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
