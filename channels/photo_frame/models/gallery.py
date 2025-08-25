"""
Gallery (Sub-channel) Data Models for Photo Frame Channel
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    # Fallback for environments without Pydantic
    PYDANTIC_AVAILABLE = False
    BaseModel = object
    def Field(*args, **kwargs):
        return None


if PYDANTIC_AVAILABLE:
    class GalleryBase(BaseModel):
        """Base gallery model with common fields"""
        name: str = Field(..., description="Gallery name")
        description: str = Field(default="", description="Gallery description")
        tags: List[str] = Field(default_factory=list, description="Gallery tags")

    class GalleryCreate(GalleryBase):
        """Model for creating a new gallery"""
        display_settings: Optional[Dict[str, Any]] = Field(default=None, description="Custom display settings")

    class GalleryUpdate(BaseModel):
        """Model for updating an existing gallery"""
        name: Optional[str] = Field(default=None, description="Gallery name")
        description: Optional[str] = Field(default=None, description="Gallery description") 
        tags: Optional[List[str]] = Field(default=None, description="Gallery tags")
        cover_image_id: Optional[str] = Field(default=None, description="Cover image ID")
        display_settings: Optional[Dict[str, Any]] = Field(default=None, description="Display settings")

else:
    # Fallback classes for environments without Pydantic
    class GalleryBase:
        def __init__(self, name: str, description: str = "", tags: List[str] = None):
            self.name = name
            self.description = description
            self.tags = tags or []

    class GalleryCreate(GalleryBase):
        def __init__(self, name: str, description: str = "", tags: List[str] = None, display_settings: Dict[str, Any] = None):
            super().__init__(name, description, tags)
            self.display_settings = display_settings

    class GalleryUpdate:
        def __init__(self, name: str = None, description: str = None, tags: List[str] = None, 
                     cover_image_id: str = None, display_settings: Dict[str, Any] = None):
            self.name = name
            self.description = description
            self.tags = tags
            self.cover_image_id = cover_image_id
            self.display_settings = display_settings


class Gallery:
    """Complete gallery model with all fields"""
    
    def __init__(self, id: str, name: str, description: str = "", content_ids: List[str] = None,
                 tags: List[str] = None, created: str = None, modified: str = None,
                 image_count: int = 0, cover_image_id: str = None, display_settings: Dict[str, Any] = None):
        self.id = id
        self.name = name
        self.description = description
        self.content_ids = content_ids or []
        self.tags = tags or []
        self.created = created or datetime.now(timezone.utc).isoformat()
        self.modified = modified or datetime.now(timezone.utc).isoformat()
        self.image_count = image_count
        self.cover_image_id = cover_image_id
        self.display_settings = display_settings or self._get_default_settings()

    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default display settings"""
        return {
            "order_mode": "added",
            "crop_mode": "smart_crop",
            "transition_effect": "fade",
            "update_interval_value": 30,
            "update_interval_unit": "minutes",
            "slideshow_enabled": True
        }

    @classmethod
    def create_new(cls, gallery_data: GalleryCreate, gallery_id: str, default_settings: Dict[str, Any] = None) -> "Gallery":
        """Create a new gallery from creation data"""
        now = datetime.now(timezone.utc).isoformat()
        
        # Use provided settings or defaults
        if hasattr(gallery_data, 'display_settings') and gallery_data.display_settings:
            display_settings = gallery_data.display_settings
        else:
            # Create from defaults
            display_settings = default_settings or {}
            if not display_settings:
                display_settings = {
                    "order_mode": "added",
                    "crop_mode": "smart_crop",
                    "transition_effect": "fade",
                    "update_interval_value": 30,
                    "update_interval_unit": "minutes",
                    "slideshow_enabled": True
                }
        
        return cls(
            id=gallery_id,
            name=gallery_data.name,
            description=gallery_data.description,
            tags=gallery_data.tags,
            content_ids=[],
            created=now,
            modified=now,
            image_count=0,
            cover_image_id=None,
            display_settings=display_settings
        )

    def update_from_data(self, update_data: GalleryUpdate) -> None:
        """Update gallery with new data"""
        if hasattr(update_data, 'name') and update_data.name is not None:
            self.name = update_data.name
        if hasattr(update_data, 'description') and update_data.description is not None:
            self.description = update_data.description
        if hasattr(update_data, 'tags') and update_data.tags is not None:
            self.tags = update_data.tags
        if hasattr(update_data, 'cover_image_id') and update_data.cover_image_id is not None:
            self.cover_image_id = update_data.cover_image_id
        if hasattr(update_data, 'display_settings') and update_data.display_settings is not None:
            self.display_settings = update_data.display_settings
        
        self.modified = datetime.now(timezone.utc).isoformat()

    def add_images(self, image_ids: List[str]) -> None:
        """Add images to gallery"""
        for image_id in image_ids:
            if image_id not in self.content_ids:
                self.content_ids.append(image_id)
        
        self.image_count = len(self.content_ids)
        self.modified = datetime.now(timezone.utc).isoformat()
        
        # Set cover image if none exists
        if self.content_ids and not self.cover_image_id:
            self.cover_image_id = self.content_ids[0]

    def remove_images(self, image_ids: List[str]) -> None:
        """Remove images from gallery"""
        self.content_ids = [cid for cid in self.content_ids if cid not in image_ids]
        self.image_count = len(self.content_ids)
        self.modified = datetime.now(timezone.utc).isoformat()
        
        # Clear cover image if it was removed
        if self.cover_image_id in image_ids:
            self.cover_image_id = self.content_ids[0] if self.content_ids else None

    def set_images(self, image_ids: List[str]) -> None:
        """Replace all images in gallery"""
        self.content_ids = image_ids.copy()
        self.image_count = len(self.content_ids)
        self.modified = datetime.now(timezone.utc).isoformat()
        
        # Set cover image
        if self.content_ids and not self.cover_image_id:
            self.cover_image_id = self.content_ids[0]

    def reorder_images(self, dragged_id: str, target_id: str) -> bool:
        """Reorder images by moving dragged_id after target_id"""
        if dragged_id not in self.content_ids or target_id not in self.content_ids:
            return False
        
        # Remove dragged image
        self.content_ids.remove(dragged_id)
        
        # Insert after target
        target_index = self.content_ids.index(target_id)
        self.content_ids.insert(target_index + 1, dragged_id)
        
        self.modified = datetime.now(timezone.utc).isoformat()
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "contentIds": self.content_ids,  # Note: using camelCase for frontend compatibility
            "tags": self.tags,
            "created": self.created,
            "modified": self.modified,
            "imageCount": self.image_count,
            "coverImageId": self.cover_image_id,
            "displaySettings": self.display_settings
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Gallery":
        """Create gallery from dictionary"""
        # Handle both camelCase (frontend) and snake_case (backend)
        content_ids = data.get("contentIds", data.get("content_ids", []))
        image_count = data.get("imageCount", data.get("image_count", 0))
        cover_image_id = data.get("coverImageId", data.get("cover_image_id"))
        display_settings_data = data.get("displaySettings", data.get("display_settings", {}))
        
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            content_ids=content_ids,
            tags=data.get("tags", []),
            created=data["created"],
            modified=data["modified"],
            image_count=image_count,
            cover_image_id=cover_image_id,
            display_settings=display_settings_data if display_settings_data else {}
        )
