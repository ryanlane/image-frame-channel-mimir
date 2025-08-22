import os
import json
import asyncio
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, Optional, List
from pathlib import Path
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse

# Handle imports for both standalone and platform usage
try:
    from .utils.image_processor import ImageProcessor
    from .utils.database import PhotoFrameDB
except ImportError:
    # Fallback for standalone testing
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from utils.image_processor import ImageProcessor
    from utils.database import PhotoFrameDB

class PhotoFrameChannel:
    """
    Photo Frame channel for Mimir Platform v2.4
    Provides digital photo frame functionality with intelligent image management
    """
    
    def __init__(self, channel_dir: str):
        self.channel_dir = Path(channel_dir)
        self.config_path = self.channel_dir / "config.json"
        self._config = self._load_config()
        
        # Initialize components
        self.db = PhotoFrameDB(self.channel_dir / "data" / "photo_frame.db")
        self.image_processor = ImageProcessor(
            upload_dir=self.channel_dir / "assets" / "uploads",
            thumb_dir=self.channel_dir / "data" / "thumbs"
        )
        
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
    
    async def render_image(
        self, 
        resolution: Tuple[int, int], 
        orientation: str, 
        settings: Dict[str, Any]
    ) -> str:
        """
        Generate/select next image for display
        
        Args:
            resolution: (width, height) in pixels
            orientation: "landscape" or "portrait"
            settings: User configuration from Mimir Platform
            
        Returns:
            Relative path to image file
        """
        try:
            # Get next image based on slideshow settings
            image_record = await self._get_next_image(settings)
            
            if not image_record:
                # No images available, return placeholder
                return self.config["placeholder_image"]
            
            # Process image for display
            output_path = await self._process_image_for_display(
                image_record, resolution, orientation, settings
            )
            
            # Update statistics
            await self._update_image_stats(image_record["id"])
            
            self.current_image_id = image_record["id"]
            self.last_update = datetime.now(timezone.utc)
            self.last_error = None
            
            return self.config["current_image"]
            
        except Exception as e:
            self.last_error = str(e)
            # Return last successful image or placeholder
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
    
    def get_router(self) -> APIRouter:
        """Return FastAPI router for channel-specific endpoints"""
        router = APIRouter()
        
        @router.get("/images")
        async def list_images():
            """List all uploaded images with metadata"""
            images = self.db.get_all_images()
            return JSONResponse(images)

        @router.post("/upload")
        async def upload_images(files: List[UploadFile] = File(...)):
            """Handle image uploads"""
            results = []
            
            for file in files:
                try:
                    # Process upload
                    image_data = await self.image_processor.save_upload(file)
                    
                    # Add to database
                    image_id = self.db.add_image(image_data)
                    
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
            
            success = self.db.update_image(image_id, {
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
                raise HTTPException(status_code=404, detail="Image not found")

        @router.post("/images/{image_id}/toggle")
        async def toggle_image(image_id: int):
            """Enable/disable image in slideshow"""
            success = self.db.toggle_image_enabled(image_id)
            
            if success:
                image = self.db.get_image(image_id)
                return JSONResponse({"success": True, "enabled": image["enabled"]})
            else:
                raise HTTPException(status_code=404, detail="Image not found")

        @router.delete("/images/{image_id}")
        async def delete_image(image_id: int):
            """Delete image from collection"""
            success = self.db.delete_image(image_id)
            
            if success:
                return JSONResponse({"success": True})
            else:
                raise HTTPException(status_code=404, detail="Image not found")
        
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
        
        return router
    
    async def _get_next_image(self, settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Select next image based on slideshow settings"""
        if not settings.get("slideshow_enabled", True):
            # If slideshow disabled, return current image
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
        self.db.update_image(image_id, {
            "times_shown": self.db.get_image(image_id)["times_shown"] + 1,
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
        images = self.db.get_enabled_images()
        if images:
            return await self._render_simple_fallback(images[0])
        
        # Use placeholder
        return self.config["placeholder_image"]
    
    async def _render_simple_fallback(self, image_record):
        """Render a simple fallback version of an image"""
        # Simple implementation for fallback
        return self.config["placeholder_image"]
