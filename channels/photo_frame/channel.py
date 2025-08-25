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
    from utils.database import PhotoFrameDB
    from utils.file_metadata import FileMetadataManager
except ImportError:
    # Fallback for standalone testing
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from utils.image_processor import ImageProcessor
    from utils.database import PhotoFrameDB
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
    """
    
    def __init__(self, channel_dir: str):
        self.channel_dir = Path(channel_dir)
        self.config_path = self.channel_dir / "config.json"
        self._config = self._load_config()
        
        # Initialize components
        # Keep database for settings only
        self.db = PhotoFrameDB(self.channel_dir / "data" / "photo_frame.db")
        
        # Use file-based metadata for images
        self.metadata = FileMetadataManager(self.channel_dir / "assets" / "uploads")
        
        # Image processor with new thumbnail approach
        self.image_processor = ImageProcessor(
            upload_dir=self.channel_dir / "assets" / "uploads"
        )
        
        # Gallery management (keep existing file-based approach)
        self.galleries_file = self.channel_dir / "data" / "galleries.json"
        self._galleries = self._load_galleries()
        
        # State tracking
        self.last_update = None
        self.last_error = None
        self.current_image_id = None
        
        # NEW: Initialize services for improved architecture
        self.settings_manager = SettingsManager()  # Add missing settings manager
        self.gallery_service = GalleryService(self.channel_dir)
        self.image_service = ImageService(
            self.channel_dir / "assets" / "uploads", 
            self.image_processor
        )
        self.rendering_service = RenderingService(self.channel_dir)
        self.storage_service = StorageService(self.channel_dir)
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load channel configuration"""
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    def _load_galleries(self) -> List[Dict[str, Any]]:
        """Load galleries (sub-channels) configuration"""
        if self.galleries_file.exists():
            with open(self.galleries_file, 'r') as f:
                return json.load(f)
        return []
    
    def _save_galleries(self):
        """Save galleries configuration"""
        self.galleries_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.galleries_file, 'w') as f:
            json.dump(self._galleries, f, indent=2)
    
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
            subchannel_id: Gallery ID to select from (required for proper settings)
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
                    current_settings = self.get_gallery_settings(subchannel_id)
                    print(f"📋 Using gallery-specific settings: {current_settings}")
                except ValueError:
                    print(f"⚠️ Gallery '{subchannel_id}' not found, using global settings")
                    current_settings = settings or {}
            else:
                current_settings = settings or {}
            
            # Get next image based on gallery selection or all images
            if subchannel_id:
                gallery = self._find_gallery(subchannel_id)
                if gallery:
                    image_record = await self._get_next_image_from_gallery(gallery, current_settings)
                else:
                    print(f"⚠️ Gallery '{subchannel_id}' not found, using all images")
                    image_record = await self._get_next_image(current_settings)
            else:
                image_record = await self._get_next_image(current_settings)
            
            if not image_record:
                # No images available, use placeholder
                placeholder_path = self.channel_dir / "placeholder.jpg"
                if placeholder_path.exists():
                    # Process placeholder for this resolution using old method signature
                    await self._process_placeholder_for_display(
                        placeholder_path, output_path, resolution, current_settings
                    )
                    print(f"✅ Used placeholder image for {resolution_folder}")
                    return str(output_path)
                else:
                    raise Exception("No images available and no placeholder found")
            
            # Process image for display using the existing method
            await self._process_image_for_display(
                image_record, resolution, orientation, current_settings
            )
            
            # Copy the processed image to our resolution-specific location
            legacy_current = self.channel_dir / self.config["current_image"]
            if legacy_current.exists():
                import shutil
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
                    import shutil
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
            "database_ok": self.db.check_health(),
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
            self.db, self._config
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
    
    async def _get_next_image(self, settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Select next image based on slideshow settings"""
        if not settings.get("slideshow_enabled", True):
            # If slideshow disabled, return current image
            if self.current_image_id:
                return self.metadata.get_image_by_id(str(self.current_image_id))
        
        order_mode = settings.get("order_mode", "added")
        all_images = self.metadata.get_all_images()
        enabled_images = [img for img in all_images if img.get("enabled", True)]
        
        if not enabled_images:
            return None
        
        if order_mode == "random":
            import random
            return random.choice(enabled_images)
        elif order_mode == "custom":
            # Sort by custom sort_order, then by least recently shown
            return self._get_next_by_custom_order(enabled_images)
        else:  # "added"
            # Sort by creation date, prefer never shown
            return self._get_next_by_date_added(enabled_images)
    
    def _get_next_by_custom_order(self, images):
        """Get next image by custom order"""
        # Sort by sort_order, then by times_shown (least shown first)
        return sorted(images, key=lambda x: (x.get("sort_order", 0), x.get("times_shown", 0)))[0]
    
    def _get_next_by_date_added(self, images):
        """Get next image by date added"""
        # Sort by times_shown (least shown first), then by creation date
        return sorted(images, key=lambda x: (x.get("times_shown", 0), x.get("created_at", "")))[0]
    
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
    # Gallery (Sub-Channel) Support Methods
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
    
    def get_subchannels(self) -> List[Dict[str, Any]]:
        """Get all galleries (sub-channels)"""
        return self._galleries.copy()
    
    def create_subchannel(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new gallery"""
        if "name" not in data:
            raise ValueError("Gallery name is required")
        
        gallery_id = self._generate_subchannel_id(data["name"])
        
        # Get default settings from config or use hardcoded defaults
        default_settings = self._config.get("settings", {}).get("defaults", {})
        
        gallery = {
            "id": gallery_id,
            "name": data["name"],
            "description": data.get("description", ""),
            "contentIds": [],
            "tags": data.get("tags", []),
            "created": datetime.now(timezone.utc).isoformat(),
            "modified": datetime.now(timezone.utc).isoformat(),
            "imageCount": 0,
            "coverImageId": None,
            # Display settings for this gallery
            "displaySettings": {
                "order_mode": default_settings.get("order_mode", "added"),
                "crop_mode": default_settings.get("crop_mode", "smart_crop"),
                "transition_effect": default_settings.get("transition_effect", "fade"),
                "update_interval_value": default_settings.get("update_interval_value", 30),
                "update_interval_unit": default_settings.get("update_interval_unit", "minutes"),
                "slideshow_enabled": default_settings.get("slideshow_enabled", True)
            }
        }
        
        self._galleries.append(gallery)
        self._save_galleries()
        
        return gallery
    
    def update_subchannel(self, subchannel_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing gallery"""
        for i, gallery in enumerate(self._galleries):
            if gallery["id"] == subchannel_id:
                # Update allowed fields
                if "name" in data:
                    gallery["name"] = data["name"]
                if "description" in data:
                    gallery["description"] = data["description"]
                if "tags" in data:
                    gallery["tags"] = data["tags"]
                if "cover_image_id" in data:
                    gallery["coverImageId"] = data["cover_image_id"]
                
                # Update display settings if provided
                if "displaySettings" in data:
                    # Ensure displaySettings exists
                    if "displaySettings" not in gallery:
                        gallery["displaySettings"] = {}
                    
                    # Validate and update each setting
                    display_settings = data["displaySettings"]
                    for key, value in display_settings.items():
                        if key in ["order_mode", "crop_mode", "transition_effect", "update_interval_unit"]:
                            gallery["displaySettings"][key] = value
                        elif key in ["update_interval_value"]:
                            gallery["displaySettings"][key] = int(value)
                        elif key in ["slideshow_enabled"]:
                            gallery["displaySettings"][key] = bool(value)
                
                gallery["modified"] = datetime.now(timezone.utc).isoformat()
                self._save_galleries()
                return gallery
        
        raise ValueError(f"Gallery '{subchannel_id}' not found")
    
    def delete_subchannel(self, subchannel_id: str) -> bool:
        """Delete a gallery (removes gallery but keeps images)"""
        for i, gallery in enumerate(self._galleries):
            if gallery["id"] == subchannel_id:
                del self._galleries[i]
                self._save_galleries()
                return True
        
        raise ValueError(f"Gallery '{subchannel_id}' not found")
    
    def assign_content_to_subchannel(
        self, 
        subchannel_id: str, 
        content_ids: List[str], 
        action: str = "add"
    ) -> bool:
        """Assign images to a gallery"""
        gallery = self._find_gallery(subchannel_id)
        if not gallery:
            raise ValueError(f"Gallery '{subchannel_id}' not found")
        
        # Validate that content_ids are valid image IDs
        all_images = self.metadata.get_all_images()
        valid_image_ids = {str(img["id"]) for img in all_images}
        invalid_ids = set(content_ids) - valid_image_ids
        if invalid_ids:
            raise ValueError(f"Invalid image IDs: {', '.join(invalid_ids)}")
        
        if action == "set":
            gallery["contentIds"] = content_ids.copy()
        elif action == "add":
            # Add new images, avoid duplicates
            for content_id in content_ids:
                if content_id not in gallery["contentIds"]:
                    gallery["contentIds"].append(content_id)
        elif action == "remove":
            gallery["contentIds"] = [
                c for c in gallery["contentIds"] if c not in content_ids
            ]
        else:
            raise ValueError(f"Invalid action '{action}'. Use 'set', 'add', or 'remove'")
        
        # Update metadata
        gallery["imageCount"] = len(gallery["contentIds"])
        gallery["modified"] = datetime.now(timezone.utc).isoformat()
        
        # Set cover image if none exists and we have images
        if gallery["contentIds"] and not gallery["coverImageId"]:
            gallery["coverImageId"] = gallery["contentIds"][0]
        
        self._save_galleries()
        return True
    
    def get_subchannel_content(
        self, 
        subchannel_id: str, 
        limit: int = None, 
        offset: int = None
    ) -> Dict[str, Any]:
        """Get images in a gallery with pagination"""
        gallery = self._find_gallery(subchannel_id)
        if not gallery:
            raise ValueError(f"Gallery '{subchannel_id}' not found")
        
        content_ids = gallery["contentIds"]
        total_count = len(content_ids)
        
        # Apply pagination
        if offset:
            content_ids = content_ids[offset:]
        if limit:
            content_ids = content_ids[:limit]
        
        # Get detailed image data
        images = []
        for content_id in content_ids:
            image_data = self.metadata.get_image_by_id(str(content_id))
            if image_data:
                images.append({
                    "id": str(image_data["id"]),
                    "name": image_data.get("title", image_data["original_name"]),
                    "filename": image_data["filename"],
                    "thumbnailUrl": f"/api/channels/{self.id}/assets/uploads/{Path(image_data['filename']).stem}.thumb.jpg",
                    "uploadUrl": f"/api/channels/{self.id}/assets/uploads/{image_data['filename']}",
                    "enabled": image_data.get("enabled", True),
                    "uploaded": image_data["upload_time"],
                    "description": image_data.get("description", ""),
                    "tags": image_data.get("tags", [])
                })
        
        return {
            "content": images,
            "totalCount": total_count,
            "limit": limit,
            "offset": offset or 0
        }
    
    def _find_gallery(self, gallery_id: str) -> Optional[Dict[str, Any]]:
        """Find a gallery by ID"""
        for gallery in self._galleries:
            if gallery["id"] == gallery_id:
                return gallery
        return None
    
    def get_gallery_settings(self, gallery_id: str) -> Dict[str, Any]:
        """Get display settings for a specific gallery"""
        gallery = self._find_gallery(gallery_id)
        if not gallery:
            raise ValueError(f"Gallery '{gallery_id}' not found")
        
        # Return display settings, falling back to defaults if not set
        default_settings = self._config.get("settings", {}).get("defaults", {})
        display_settings = gallery.get("displaySettings", {})
        
        return {
            "order_mode": display_settings.get("order_mode", default_settings.get("order_mode", "added")),
            "crop_mode": display_settings.get("crop_mode", default_settings.get("crop_mode", "smart_crop")),
            "transition_effect": display_settings.get("transition_effect", default_settings.get("transition_effect", "fade")),
            "update_interval_value": display_settings.get("update_interval_value", default_settings.get("update_interval_value", 30)),
            "update_interval_unit": display_settings.get("update_interval_unit", default_settings.get("update_interval_unit", "minutes")),
            "slideshow_enabled": display_settings.get("slideshow_enabled", default_settings.get("slideshow_enabled", True))
        }
    
    def update_gallery_settings(self, gallery_id: str, settings: Dict[str, Any]) -> bool:
        """Update display settings for a specific gallery"""
        gallery = self._find_gallery(gallery_id)
        if not gallery:
            raise ValueError(f"Gallery '{gallery_id}' not found")
        
        # Validate settings (synchronous validation)
        valid_orders = ["added", "random", "custom"]
        valid_crops = ["smart_crop", "letterbox", "stretch"]
        valid_transitions = ["fade", "slide", "none"]
        valid_units = ["days", "hours", "minutes", "seconds"]
        
        if "order_mode" in settings and settings["order_mode"] not in valid_orders:
            raise ValueError(f"Invalid order_mode. Must be one of: {', '.join(valid_orders)}")
        if "crop_mode" in settings and settings["crop_mode"] not in valid_crops:
            raise ValueError(f"Invalid crop_mode. Must be one of: {', '.join(valid_crops)}")
        if "transition_effect" in settings and settings["transition_effect"] not in valid_transitions:
            raise ValueError(f"Invalid transition_effect. Must be one of: {', '.join(valid_transitions)}")
        if "update_interval_unit" in settings and settings["update_interval_unit"] not in valid_units:
            raise ValueError(f"Invalid update_interval_unit. Must be one of: {', '.join(valid_units)}")
        if "update_interval_value" in settings:
            try:
                value = int(settings["update_interval_value"])
                if value < 1:
                    raise ValueError("update_interval_value must be at least 1")
            except (TypeError, ValueError):
                raise ValueError("update_interval_value must be a valid positive integer")
        
        # Ensure displaySettings exists
        if "displaySettings" not in gallery:
            gallery["displaySettings"] = {}
        
        # Update settings
        for key, value in settings.items():
            if key in ["order_mode", "crop_mode", "transition_effect", "update_interval_unit"]:
                gallery["displaySettings"][key] = value
            elif key in ["update_interval_value"]:
                gallery["displaySettings"][key] = int(value)
            elif key in ["slideshow_enabled"]:
                gallery["displaySettings"][key] = bool(value)
        
        gallery["modified"] = datetime.now(timezone.utc).isoformat()
        self._save_galleries()
        return True
    
    async def _get_next_image_from_gallery(
        self, 
        gallery: Dict[str, Any], 
        settings: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """Get next image from a specific gallery"""
        if not gallery["contentIds"]:
            return None
        
        # Get image data for images in this gallery
        gallery_images = []
        for content_id in gallery["contentIds"]:
            image_data = self.metadata.get_image_by_id(str(content_id))
            if image_data and image_data.get("enabled", True):
                gallery_images.append(image_data)
        
        if gallery_images:
            # TODO: Implement proper rotation logic based on settings
            # For now, return first available image
            return gallery_images[0]
        
        return None
    
    def reorder_gallery_images(self, gallery_id: str, dragged_id: str, target_id: str) -> bool:
        """
        Reorder images within a specific gallery's contentIds array
        
        Args:
            gallery_id: ID of the gallery to reorder images in
            dragged_id: ID of the image being moved
            target_id: ID of the image to place the dragged image before
            
        Returns:
            bool: True if reordering was successful
            
        Raises:
            ValueError: If gallery or images not found
        """
        from datetime import datetime, timezone
        
        # Find the gallery
        gallery = self._find_gallery(gallery_id)
        if not gallery:
            raise ValueError(f"Gallery '{gallery_id}' not found")
        
        content_ids = gallery["contentIds"]
        
        # Validate that both images exist in the gallery
        if dragged_id not in content_ids:
            raise ValueError(f"Image '{dragged_id}' not found in gallery '{gallery_id}'")
        if target_id not in content_ids:
            raise ValueError(f"Target image '{target_id}' not found in gallery '{gallery_id}'")
        
        # Remove the dragged image from its current position
        content_ids.remove(dragged_id)
        
        # Find the new position (before the target)
        target_index = content_ids.index(target_id)
        
        # Insert the dragged image at the new position
        content_ids.insert(target_index, dragged_id)
        
        # Update the gallery
        gallery["contentIds"] = content_ids
        gallery["modified"] = datetime.now(timezone.utc).isoformat()
        
        # Save the changes
        self._save_galleries()
        
        return True
