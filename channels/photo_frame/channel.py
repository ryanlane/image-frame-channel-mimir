import os
import json
import asyncio
import re
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, Optional, List
from pathlib import Path
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse

# Handle imports for both standalone and platform usage
try:
    from .utils.image_processor import ImageProcessor
    from .utils.database import PhotoFrameDB
    from .utils.file_metadata import FileMetadataManager
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
    
    # async def render_image(
    #     self, 
    #     resolution: Tuple[int, int], 
    #     orientation: str, 
    #     settings: Dict[str, Any]
    # ) -> str:
    #     """
    #     Generate/select next image for display
        
    #     Args:
    #         resolution: (width, height) in pixels
    #         orientation: "landscape" or "portrait"
    #         settings: User configuration from Mimir Platform
            
    #     Returns:
    #         Relative path to image file
    #     """
    #     try:
    #         # Get next image based on slideshow settings
    #         image_record = await self._get_next_image(settings)
            
    #         if not image_record:
    #             # No images available, return placeholder
    #             return self.config["placeholder_image"]
            
    #         # Process image for display
    #         output_path = await self._process_image_for_display(
    #             image_record, resolution, orientation, settings
    #         )
            
    #         # Update statistics
    #         await self._update_image_stats(image_record["id"])
            
    #         self.current_image_id = image_record["id"]
    #         self.last_update = datetime.now(timezone.utc)
    #         self.last_error = None
            
    #         return self.config["current_image"]
            
    #     except Exception as e:
    #         self.last_error = str(e)
    #         # Return last successful image or placeholder
    #         return await self._get_fallback_image()
    
    
    async def render_image(self, resolution: tuple, orientation: str = "landscape", settings: dict = None, subchannel_id: str = None):
        """
        Render image for specific display resolution using resolution-based folder structure.
        Creates images in current/{width}x{height}/ subfolders for efficient sharing.
        
        Args:
            resolution: (width, height) in pixels
            orientation: "landscape" or "portrait"
            settings: User configuration from Mimir Platform
            subchannel_id: Optional gallery ID to select from
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
            
            # Get current settings
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
        
        @router.get("/images")
        async def list_images():
            """List all uploaded images with metadata"""
            images = self.metadata.get_all_images()
            return JSONResponse(images)

        @router.post("/upload")
        async def upload_images(files: List[UploadFile] = File(...)):
            """Handle image uploads"""
            results = []
            
            for file in files:
                try:
                    # Process upload (saves image and thumbnail)
                    image_data = await self.image_processor.save_upload(file)
                    
                    # Add metadata file
                    image_id = self.metadata.add_image(image_data)
                    
                    results.append({
                        "filename": file.filename,
                        "success": True,
                        "image_id": image_id
                    })
                    
                except Exception as e:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": str(e)
                    })
            
            return JSONResponse({"results": results})

        @router.put("/images/{image_id}")
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
            """Update image metadata and crop settings"""
            
            updates = {
                "title": title,
                "description": description,
                "crop_x": crop_x,
                "crop_y": crop_y,
                "crop_width": crop_width,
                "crop_height": crop_height,
                "preserve_aspect_ratio": preserve_aspect_ratio
            }
            
            success = self.metadata.update_image(str(image_id), updates)
            
            if success:
                return JSONResponse({"success": True})
            else:
                raise HTTPException(status_code=404, detail="Image not found")

        @router.post("/images/{image_id}/toggle")
        async def toggle_image(image_id: int):
            """Enable/disable image in slideshow"""
            success = self.metadata.toggle_image_enabled(str(image_id))
            
            if success:
                image = self.metadata.get_image(str(image_id))
                return JSONResponse({"success": True, "enabled": image["enabled"] if image else False})
            else:
                raise HTTPException(status_code=404, detail="Image not found")

        @router.delete("/images/{image_id}")
        async def delete_image(image_id: int):
            """Delete image from collection"""
            success = self.metadata.delete_image(str(image_id))
            
            if success:
                return JSONResponse({"success": True})
            else:
                raise HTTPException(status_code=404, detail="Image not found")

        @router.post("/images/reorder")
        async def reorder_images(request: Request):
            """Reorder images by updating sort_order"""
            try:
                data = await request.json()
                dragged_id = data.get("dragged_id")
                target_id = data.get("target_id")
                
                if not dragged_id or not target_id:
                    raise HTTPException(status_code=400, detail="Both dragged_id and target_id required")
                
                # Get all images with current sort order
                images = self.metadata.get_all_images()
                images.sort(key=lambda x: x.get("sort_order", 0))
                
                # Find the dragged and target images
                dragged_img = next((img for img in images if img["id"] == dragged_id), None)
                target_img = next((img for img in images if img["id"] == target_id), None)
                
                if not dragged_img or not target_img:
                    raise HTTPException(status_code=404, detail="Image not found")
                
                # Remove dragged image from list
                images = [img for img in images if img["id"] != dragged_id]
                
                # Find target position and insert dragged image
                target_index = next(i for i, img in enumerate(images) if img["id"] == target_id)
                images.insert(target_index, dragged_img)
                
                # Update sort_order for all images
                for i, img in enumerate(images):
                    self.metadata.update_image(str(img["id"]), {"sort_order": i})
                
                return JSONResponse({"success": True})
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.get("/settings")
        async def get_settings():
            """Get current photo frame configuration"""
            # Get settings from database or use defaults
            settings = self.db.get_settings()
            if not settings:
                # Return defaults from config if no settings stored
                settings = self._config.get("settings", {}).get("defaults", {})
            
            return JSONResponse({
                "slideshow_enabled": {
                    "type": "boolean",
                    "value": settings.get("slideshow_enabled", True)
                },
                "order_mode": {
                    "type": "string", 
                    "value": settings.get("order_mode", "added")
                },
                "crop_mode": {
                    "type": "string",
                    "value": settings.get("crop_mode", "smart_crop")
                },
                "transition_effect": {
                    "type": "string",
                    "value": settings.get("transition_effect", "fade")
                },
                "update_interval_unit": {
                    "type": "string",
                    "value": settings.get("update_interval_unit", "minutes")
                },
                "update_interval_value": {
                    "type": "integer",
                    "value": settings.get("update_interval_value", 30)
                }
            })

        @router.put("/settings")
        async def update_settings(request: Request):
            """Update photo frame configuration"""
            try:
                settings_data = await request.json()
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid JSON data")
            
            # Validate settings
            errors = await self.validate_settings(settings_data)
            if errors:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "errors": errors
                    }
                )
            
            # Update settings in database
            success = self.db.update_settings(settings_data)
            
            if success:
                return JSONResponse({"success": True})
            else:
                raise HTTPException(status_code=500, detail="Failed to update settings")

        @router.get("/hardware")
        async def get_hardware():
            """Get Inky display hardware info"""
            # Mock hardware info for development
            return JSONResponse({
                "display": "Inky",
                "resolution": [800, 600],
                "orientation": "landscape"
            })

        @router.get("/data/thumbs/{filename}")
        async def get_thumbnail(filename: str):
            """Serve thumbnail images (legacy endpoint)"""
            # Convert to new thumbnail format
            base_name = Path(filename).stem
            thumb_filename = f"{base_name}.thumb.jpg"
            thumb_path = self.channel_dir / "assets" / "uploads" / thumb_filename
            
            if not thumb_path.exists():
                raise HTTPException(status_code=404, detail="Thumbnail not found")
            
            return FileResponse(
                path=str(thumb_path),
                media_type="image/jpeg",
                headers={"Cache-Control": "max-age=3600"}
            )

        @router.get("/assets/uploads/{filename}")
        async def get_upload_file(filename: str):
            """Serve uploaded files (images and thumbnails)"""
            file_path = self.channel_dir / "assets" / "uploads" / filename
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="File not found")
            
            # Determine media type
            if filename.endswith('.jpg') or filename.endswith('.jpeg'):
                media_type = "image/jpeg"
            elif filename.endswith('.png'):
                media_type = "image/png"
            elif filename.endswith('.gif'):
                media_type = "image/gif"
            else:
                media_type = "application/octet-stream"
            
            return FileResponse(
                path=str(file_path),
                media_type=media_type,
                headers={"Cache-Control": "max-age=3600"}
            )

        @router.post("/regenerate-thumbnails")
        async def regenerate_thumbnails():
            """Regenerate thumbnails for all existing images"""
            try:
                count = await self._regenerate_all_thumbnails()
                return JSONResponse({"success": True, "thumbnails_generated": count})
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to regenerate thumbnails: {str(e)}")

        @router.post("/rebuild-database")
        async def rebuild_database():
            """Rebuild database from existing files in uploads directory"""
            try:
                count = await self._rebuild_database_from_files()
                return JSONResponse({"success": True, "images_added": count})
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to rebuild database: {str(e)}")

        @router.post("/sync-filesystem")
        async def sync_filesystem():
            """Sync metadata files with filesystem state"""
            try:
                results = self.metadata.sync_filesystem()
                return JSONResponse({"success": True, **results})
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to sync filesystem: {str(e)}")

        @router.post("/regenerate-thumbnails")
        async def regenerate_thumbnails():
            """Regenerate all thumbnails using the new co-located approach"""
            try:
                results = await self._regenerate_colocated_thumbnails()
                return JSONResponse({"success": True, **results})
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to regenerate thumbnails: {str(e)}")
        
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
                return self.metadata.get_image(str(self.current_image_id))
            
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
    
    async def _update_image_stats(self, image_id: int):
        """Update image display statistics"""
        image = self.metadata.get_image(str(image_id))
        if image:
            self.metadata.update_image(str(image_id), {
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
        
        gallery = {
            "id": gallery_id,
            "name": data["name"],
            "description": data.get("description", ""),
            "contentIds": [],
            "tags": data.get("tags", []),
            "created": datetime.now(timezone.utc).isoformat(),
            "modified": datetime.now(timezone.utc).isoformat(),
            "imageCount": 0,
            "coverImageId": None
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
            image_data = self.metadata.get_image(str(content_id))
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
            image_data = self.metadata.get_image(str(content_id))
            if image_data and image_data.get("enabled", True):
                gallery_images.append(image_data)
        
        if gallery_images:
            # TODO: Implement proper rotation logic based on settings
            # For now, return first available image
            return gallery_images[0]
        
        return None
