"""
Photo Frame Channel with Sub-Channel (Gallery) Support
Extends the existing PhotoFrameChannel to support galleries via sub-channels
"""

import os
import json
import asyncio
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, Optional, List
from pathlib import Path

# Import the BaseChannel interface from the API service
import sys
sys.path.insert(0, '../../mimir-api/api-service')
from base_channel import BaseChannel

# Import the existing PhotoFrameChannel
try:
    from .utils.image_processor import ImageProcessor
    from .utils.database import PhotoFrameDB
except ImportError:
    # Fallback for standalone testing
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from utils.image_processor import ImageProcessor
    from utils.database import PhotoFrameDB


class PhotoFrameChannelWithGalleries(BaseChannel):
    """
    Photo Frame channel for Mimir Platform v2.4+ with Gallery (Sub-channel) Support
    Provides digital photo frame functionality with intelligent image management and galleries
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
        
        # Gallery management
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
    
    # BaseChannel abstract methods implementation
    
    async def render_image(
        self, 
        resolution: Tuple[int, int], 
        orientation: str = "landscape", 
        settings: Dict[str, Any] = None, 
        subchannel_id: str = None
    ) -> str:
        """
        Generate/select next image for display
        
        Args:
            resolution: (width, height) in pixels
            orientation: "landscape" or "portrait"
            settings: User configuration from Mimir Platform
            subchannel_id: Optional gallery ID to select from
            
        Returns:
            Relative path to image file
        """
        try:
            # Get images from specific gallery if specified
            if subchannel_id:
                gallery = self._find_gallery(subchannel_id)
                if gallery:
                    # Get next image from this gallery
                    image_record = await self._get_next_image_from_gallery(gallery, settings)
                else:
                    # Gallery not found, use all images
                    image_record = await self._get_next_image(settings)
            else:
                # Get next image from all available images
                image_record = await self._get_next_image(settings)
            
            if not image_record:
                # No images available, return placeholder
                return self.config.get("placeholder_image", "placeholder.jpg")
            
            # Process image for display
            output_path = await self._process_image_for_display(
                image_record, resolution, orientation, settings
            )
            
            return str(output_path)
            
        except Exception as e:
            self.last_error = str(e)
            print(f"Error in render_image: {e}")
            return await self._get_fallback_image()
    
    async def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, str]:
        """Validate channel settings"""
        errors = {}
        
        if "slideshow_enabled" in settings:
            if not isinstance(settings["slideshow_enabled"], bool):
                errors["slideshow_enabled"] = "Must be a boolean value"
        
        if "update_interval" in settings:
            try:
                interval = int(settings["update_interval"])
                if interval < 1:
                    errors["update_interval"] = "Must be at least 1 minute"
            except ValueError:
                errors["update_interval"] = "Must be a valid number"
        
        return errors
    
    def get_status(self) -> Dict[str, Any]:
        """Get channel status"""
        total_images = self.db.get_total_image_count()
        enabled_images = self.db.get_enabled_image_count()
        
        uploads_dir = self.channel_dir / "assets" / "uploads"
        thumbs_dir = self.channel_dir / "data" / "thumbs"
        
        def dir_size(path):
            if not path.exists():
                return 0
            return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        
        return {
            "status": "active" if enabled_images > 0 else "no_content",
            "total_images": total_images,
            "enabled_images": enabled_images,
            "galleries": len(self._galleries),
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "last_error": self.last_error,
            "storage_usage": {
                "uploads_mb": round(dir_size(uploads_dir) / 1024 / 1024, 2),
                "thumbs_mb": round(dir_size(thumbs_dir) / 1024 / 1024, 2),
                "total_mb": round((dir_size(uploads_dir) + dir_size(thumbs_dir)) / 1024 / 1024, 2)
            }
        }
    
    # Sub-channel (Gallery) support methods
    
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
        valid_image_ids = {str(img["id"]) for img in self.db.get_all_images()}
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
            image_data = self.db.get_image_by_id(int(content_id))
            if image_data:
                images.append({
                    "id": str(image_data["id"]),
                    "name": image_data.get("title", image_data["original_name"]),
                    "filename": image_data["filename"],
                    "thumbnailUrl": f"/api/channels/{self.id}/data/thumbs/{image_data['filename']}",
                    "uploadUrl": f"/api/channels/{self.id}/assets/uploads/{image_data['filename']}",
                    "enabled": image_data["enabled"],
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
    
    # Helper methods
    
    def _find_gallery(self, gallery_id: str) -> Optional[Dict[str, Any]]:
        """Find a gallery by ID"""
        for gallery in self._galleries:
            if gallery["id"] == gallery_id:
                return gallery
        return None
    
    async def _get_next_image(self, settings: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Get next image from all images (existing method)"""
        # Implementation would be similar to original PhotoFrameChannel
        # For now, return a mock result
        images = self.db.get_enabled_images()
        if images:
            return images[0]  # Simplified - would implement proper rotation logic
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
            image_data = self.db.get_image_by_id(int(content_id))
            if image_data and image_data["enabled"]:
                gallery_images.append(image_data)
        
        if gallery_images:
            # Simplified - would implement proper rotation logic
            return gallery_images[0]
        
        return None
    
    async def _process_image_for_display(
        self, 
        image_record: Dict[str, Any], 
        resolution: Tuple[int, int], 
        orientation: str, 
        settings: Dict[str, Any] = None
    ) -> str:
        """Process image for display (existing method)"""
        # This would use the existing image processing logic
        # For now, return a mock path
        return f"processed/{image_record['filename']}"
    
    async def _get_fallback_image(self) -> str:
        """Get fallback image when errors occur"""
        return self.config.get("placeholder_image", "placeholder.jpg")


# Legacy compatibility - alias to maintain existing imports
PhotoFrameChannel = PhotoFrameChannelWithGalleries
