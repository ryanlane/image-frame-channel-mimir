"""
Gallery Service - Business logic for gallery/subchannel operations
"""

import json
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path

# Use absolute imports to avoid relative import issues
try:
    from models import Gallery, GalleryCreate, GalleryUpdate, GallerySettings
except ImportError:
    # Fallback for when running from channel directory
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from models import Gallery, GalleryCreate, GalleryUpdate, GallerySettings


class GalleryService:
    """Service for managing galleries (sub-channels) operations"""
    
    def __init__(self, channel_dir: Path, default_settings: Dict[str, Any] = None):
        self.channel_dir = Path(channel_dir)
        self.galleries_file = self.channel_dir / "data" / "galleries.json"
        self.default_settings = default_settings or {}
        self._galleries = self._load_galleries()
    
    def _load_galleries(self) -> List[Gallery]:
        """Load galleries from JSON file"""
        if not self.galleries_file.exists():
            return []
        
        try:
            with open(self.galleries_file, 'r') as f:
                galleries_data = json.load(f)
            
            galleries = []
            for gallery_data in galleries_data:
                gallery = Gallery.from_dict(gallery_data)
                galleries.append(gallery)
            
            return galleries
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading galleries: {e}")
            return []
    
    def _save_galleries(self) -> None:
        """Save galleries to JSON file"""
        self.galleries_file.parent.mkdir(parents=True, exist_ok=True)
        
        galleries_data = [gallery.to_dict() for gallery in self._galleries]
        
        with open(self.galleries_file, 'w') as f:
            json.dump(galleries_data, f, indent=2)
    
    def _generate_gallery_id(self, name: str) -> str:
        """Generate unique ID from gallery name"""
        # Clean the name
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', name).lower()
        base_id = re.sub(r'\s+', '_', clean_name.strip())
        
        # Check for duplicates
        existing_ids = {gallery.id for gallery in self._galleries}
        
        if base_id not in existing_ids:
            return base_id
        
        # Add suffix for duplicates
        counter = 1
        while f"{base_id}_{counter}" in existing_ids:
            counter += 1
        return f"{base_id}_{counter}"
    
    def get_all_galleries(self) -> List[Gallery]:
        """Get all galleries"""
        return self._galleries.copy()
    
    def get_gallery(self, gallery_id: str) -> Optional[Gallery]:
        """Get gallery by ID"""
        for gallery in self._galleries:
            if gallery.id == gallery_id:
                return gallery
        return None
    
    def create_gallery(self, gallery_data: GalleryCreate) -> Gallery:
        """Create a new gallery"""
        if not gallery_data.name:
            raise ValueError("Gallery name is required")
        
        gallery_id = self._generate_gallery_id(gallery_data.name)
        gallery = Gallery.create_new(gallery_data, gallery_id, self.default_settings)
        
        self._galleries.append(gallery)
        self._save_galleries()
        
        return gallery
    
    def update_gallery(self, gallery_id: str, update_data: GalleryUpdate) -> Gallery:
        """Update an existing gallery"""
        gallery = self.get_gallery(gallery_id)
        if not gallery:
            raise ValueError(f"Gallery '{gallery_id}' not found")
        
        gallery.update_from_data(update_data)
        self._save_galleries()
        
        return gallery
    
    def delete_gallery(self, gallery_id: str) -> bool:
        """Delete a gallery (removes gallery but keeps images)"""
        for i, gallery in enumerate(self._galleries):
            if gallery.id == gallery_id:
                del self._galleries[i]
                self._save_galleries()
                return True
        
        raise ValueError(f"Gallery '{gallery_id}' not found")
    
    def assign_images_to_gallery(
        self, 
        gallery_id: str, 
        image_ids: List[str], 
        action: str = "add",
        valid_image_ids: set = None
    ) -> bool:
        """
        Assign images to a gallery
        
        Args:
            gallery_id: ID of the gallery
            image_ids: List of image IDs to assign
            action: "add", "remove", or "set"
            valid_image_ids: Set of valid image IDs for validation
        """
        gallery = self.get_gallery(gallery_id)
        if not gallery:
            raise ValueError(f"Gallery '{gallery_id}' not found")
        
        # Validate image IDs if provided
        if valid_image_ids:
            invalid_ids = set(image_ids) - valid_image_ids
            if invalid_ids:
                raise ValueError(f"Invalid image IDs: {invalid_ids}")
        
        # Perform the assignment
        if action == "set":
            gallery.set_images(image_ids)
        elif action == "add":
            gallery.add_images(image_ids)
        elif action == "remove":
            gallery.remove_images(image_ids)
        else:
            raise ValueError(f"Invalid action '{action}'. Must be 'add', 'remove', or 'set'")
        
        self._save_galleries()
        return True
    
    def get_gallery_content(
        self, 
        gallery_id: str, 
        all_images: List[Dict[str, Any]], 
        limit: int = None, 
        offset: int = None
    ) -> Dict[str, Any]:
        """
        Get images in a gallery with pagination
        
        Args:
            gallery_id: ID of the gallery
            all_images: List of all available images
            limit: Maximum number of images to return
            offset: Number of images to skip
        """
        gallery = self.get_gallery(gallery_id)
        if not gallery:
            raise ValueError(f"Gallery '{gallery_id}' not found")
        
        content_ids = gallery.content_ids
        total_count = len(content_ids)
        
        # Apply pagination
        if offset:
            content_ids = content_ids[offset:]
        if limit:
            content_ids = content_ids[:limit]
        
        # Get detailed image data
        images = []
        image_lookup = {str(img["id"]): img for img in all_images}
        
        for content_id in content_ids:
            image = image_lookup.get(content_id)
            if image:
                images.append(image)
        
        return {
            "content": images,
            "totalCount": total_count,
            "limit": limit,
            "offset": offset or 0
        }
    
    def reorder_gallery_images(self, gallery_id: str, dragged_id: str, target_id: str) -> bool:
        """
        Reorder images within a gallery
        
        Args:
            gallery_id: ID of the gallery
            dragged_id: ID of the image being moved
            target_id: ID of the image to place the dragged image before
        """
        gallery = self.get_gallery(gallery_id)
        if not gallery:
            raise ValueError(f"Gallery '{gallery_id}' not found")
        
        success = gallery.reorder_images(dragged_id, target_id)
        if success:
            self._save_galleries()
        
        return success
    
    def get_gallery_settings(self, gallery_id: str) -> Dict[str, Any]:
        """Get display settings for a specific gallery"""
        gallery = self.get_gallery(gallery_id)
        if not gallery:
            raise ValueError(f"Gallery '{gallery_id}' not found")
        
        # Return display settings, falling back to defaults if not set
        return gallery.display_settings or self.default_settings
    
    def update_gallery_settings(self, gallery_id: str, settings: Dict[str, Any]) -> bool:
        """Update display settings for a specific gallery"""
        gallery = self.get_gallery(gallery_id)
        if not gallery:
            raise ValueError(f"Gallery '{gallery_id}' not found")
        
        # Validate settings using GallerySettings
        gallery_settings = GallerySettings(settings)
        validation_errors = gallery_settings.validate()
        
        if validation_errors:
            raise ValueError(f"Invalid settings: {validation_errors}")
        
        # Update the gallery's display settings
        gallery.display_settings.update(settings)
        gallery.modified = datetime.now(timezone.utc).isoformat()
        
        self._save_galleries()
        return True
    
    def get_next_image_from_gallery(
        self, 
        gallery_id: str, 
        all_images: List[Dict[str, Any]],
        settings: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get next image from a specific gallery based on settings
        
        Args:
            gallery_id: ID of the gallery
            all_images: List of all available images
            settings: Display settings (uses gallery settings if not provided)
        """
        gallery = self.get_gallery(gallery_id)
        if not gallery or not gallery.content_ids:
            return None
        
        # Use gallery settings if not provided
        if not settings:
            settings = self.get_gallery_settings(gallery_id)
        
        # Get images in this gallery
        image_lookup = {str(img["id"]): img for img in all_images}
        gallery_images = []
        
        for content_id in gallery.content_ids:
            image = image_lookup.get(content_id)
            if image and image.get("enabled", True):
                gallery_images.append(image)
        
        if not gallery_images:
            return None
        
        # Select image based on order mode
        order_mode = settings.get("order_mode", "added")
        
        if order_mode == "random":
            import random
            return random.choice(gallery_images)
        elif order_mode == "custom":
            # Return least shown image with custom order
            return sorted(gallery_images, key=lambda x: (x.get("sort_order", 0), x.get("times_shown", 0)))[0]
        else:  # "added" - use gallery order
            # Return least shown image in gallery order
            return sorted(gallery_images, key=lambda x: x.get("times_shown", 0))[0]
    
    def remove_image_from_all_galleries(self, image_id: str) -> None:
        """Remove an image from all galleries when the image is deleted"""
        image_id_str = str(image_id)
        
        for gallery in self._galleries:
            if image_id_str in gallery.content_ids:
                gallery.remove_images([image_id_str])
        
        self._save_galleries()
    
    def get_galleries_summary(self) -> Dict[str, Any]:
        """Get summary statistics for all galleries"""
        total_galleries = len(self._galleries)
        total_images_in_galleries = sum(gallery.image_count for gallery in self._galleries)
        
        gallery_stats = []
        for gallery in self._galleries:
            gallery_stats.append({
                "id": gallery.id,
                "name": gallery.name,
                "image_count": gallery.image_count,
                "created": gallery.created,
                "modified": gallery.modified
            })
        
        return {
            "total_galleries": total_galleries,
            "total_images_in_galleries": total_images_in_galleries,
            "galleries": gallery_stats
        }
    
    def validate_galleries_data_integrity(self, all_image_ids: set) -> Dict[str, Any]:
        """Validate that all gallery content IDs reference valid images"""
        issues = []
        fixed_count = 0
        
        for gallery in self._galleries:
            invalid_ids = []
            for content_id in gallery.content_ids[:]:  # Copy to allow modification
                if content_id not in all_image_ids:
                    invalid_ids.append(content_id)
                    gallery.content_ids.remove(content_id)
                    fixed_count += 1
            
            if invalid_ids:
                issues.append({
                    "gallery_id": gallery.id,
                    "gallery_name": gallery.name,
                    "invalid_image_ids": invalid_ids
                })
                
                # Update image count and cover image
                gallery.image_count = len(gallery.content_ids)
                if gallery.cover_image_id in invalid_ids:
                    gallery.cover_image_id = gallery.content_ids[0] if gallery.content_ids else None
                
                gallery.modified = datetime.now(timezone.utc).isoformat()
        
        if fixed_count > 0:
            self._save_galleries()
        
        return {
            "issues_found": len(issues),
            "fixed_references": fixed_count,
            "issues": issues
        }
