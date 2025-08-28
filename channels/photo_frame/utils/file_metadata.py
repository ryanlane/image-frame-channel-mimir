import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone


class FileMetadataManager:
    """
    Manages image metadata using individual .meta files alongside images.
    Thumbnails are stored as .thumb.jpg files next to the original images.
    """
    
    def __init__(self, uploads_dir: Path):
        self.uploads_dir = uploads_dir
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_meta_path(self, image_filename: str) -> Path:
        """Get the path to the metadata file for an image"""
        return self.uploads_dir / f"{image_filename}.meta"
    
    def _get_thumb_path(self, image_filename: str) -> Path:
        """Get the path to the thumbnail file for an image"""
        # Always use .jpg extension for thumbnails regardless of original format
        base_name = Path(image_filename).stem
        return self.uploads_dir / f"{base_name}.thumb.jpg"
    
    def _get_image_path(self, image_filename: str) -> Path:
        """Get the path to the original image file"""
        return self.uploads_dir / image_filename
    
    def _generate_id(self, filename: str) -> str:
        """Generate a unique ID for an image based on filename and timestamp"""
        timestamp = datetime.now(timezone.utc).isoformat()
        content = f"{filename}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def add_image(self, image_data: Dict[str, Any]) -> str:
        """Add a new image with metadata. Returns the generated ID."""
        filename = image_data["filename"]
        image_id = self._generate_id(filename)
        
        # Get current max sort_order
        all_images = self.get_all_images()
        max_order = max([img.get("sort_order", 0) for img in all_images], default=0)
        
        # Create metadata
        metadata = {
            "id": image_id,
            "filename": filename,
            "original_name": image_data.get("original_name", filename),
            "title": image_data.get("title", ""),
            "description": image_data.get("description", ""),
            "width": image_data["width"],
            "height": image_data["height"],
            "enabled": True,
            "sort_order": max_order + 1,
            "times_shown": 0,
            "last_shown_at": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "crop_x": 0.0,
            "crop_y": 0.0,
            "crop_width": 100.0,
            "crop_height": 100.0,
            "preserve_aspect_ratio": False,
            "galleries": []  # List of gallery IDs this image belongs to
        }
        
        # Save metadata file
        meta_path = self._get_meta_path(filename)
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        return image_id
    
    def get_image_by_id(self, image_id: str) -> Optional[Dict[str, Any]]:
        """Get image metadata by ID"""
        for image in self.get_all_images():
            if image.get("id") == image_id:
                return image
        return None
    
    def get_image_by_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get image metadata by filename"""
        meta_path = self._get_meta_path(filename)
        if not meta_path.exists():
            return None
        
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None
    
    def get_all_images(self) -> List[Dict[str, Any]]:
        """Get all images with metadata, sorted by sort_order"""
        images = []
        
        # Find all .meta files
        for meta_path in self.uploads_dir.glob("*.meta"):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    
                # Check if the corresponding image file exists
                image_path = self._get_image_path(metadata["filename"])
                if image_path.exists():
                    images.append(metadata)
                else:
                    print(f"Warning: Orphaned metadata file {meta_path.name}, image {metadata['filename']} not found")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Invalid metadata file {meta_path.name}: {e}")
        
        # Sort by sort_order, then by created_at
        return sorted(images, key=lambda x: (x.get("sort_order", 0), x.get("created_at", "")))
    
    def get_enabled_images(self) -> List[Dict[str, Any]]:
        """Get all enabled images"""
        return [img for img in self.get_all_images() if img.get("enabled", True)]
    
    def update_image(self, image_id: str, updates: Dict[str, Any]) -> bool:
        """Update image metadata"""
        # Find the image first
        current_image = self.get_image_by_id(image_id)
        if not current_image:
            return False
        
        filename = current_image["filename"]
        meta_path = self._get_meta_path(filename)
        
        # Update metadata
        current_image.update(updates)
        
        # Save updated metadata
        try:
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(current_image, f, indent=2)
            return True
        except Exception as e:
            print(f"Error updating metadata for {filename}: {e}")
            return False
    
    def delete_image(self, image_id: str) -> bool:
        """Delete image and its metadata and thumbnail"""
        image = self.get_image_by_id(image_id)
        if not image:
            return False
        
        filename = image["filename"]
        image_path = self._get_image_path(filename)
        meta_path = self._get_meta_path(filename)
        thumb_path = self._get_thumb_path(filename)
        
        success = True
        
        # Delete files
        for path in [image_path, meta_path, thumb_path]:
            try:
                if path.exists():
                    path.unlink()
            except Exception as e:
                print(f"Error deleting {path}: {e}")
                success = False
        
        return success
    
    def toggle_image_enabled(self, image_id: str) -> bool:
        """Toggle the enabled status of an image"""
        image = self.get_image_by_id(image_id)
        if not image:
            return False
        
        return self.update_image(image_id, {"enabled": not image.get("enabled", True)})
    
    def get_image_count(self) -> int:
        """Get total number of images"""
        return len(self.get_all_images())
    
    def get_enabled_image_count(self) -> int:
        """Get number of enabled images"""
        return len(self.get_enabled_images())
    
    def sync_filesystem(self) -> Dict[str, Any]:
        """
        Sync metadata with filesystem state.
        - Find images without metadata and create default metadata
        - Remove orphaned metadata files
        - Report inconsistencies
        """
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        
        # Find all image files
        image_files = set()
        for file_path in self.uploads_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                # Skip thumbnail files
                if not file_path.name.endswith('.thumb.jpg'):
                    image_files.add(file_path.name)
        
        # Find all metadata files
        meta_files = set()
        for meta_path in self.uploads_dir.glob("*.meta"):
            meta_files.add(meta_path.name[:-5])  # Remove .meta extension
        
        # Images without metadata
        missing_metadata = image_files - meta_files
        # Metadata without images
        orphaned_metadata = meta_files - image_files
        
        results = {
            "images_found": len(image_files),
            "metadata_found": len(meta_files),
            "missing_metadata": len(missing_metadata),
            "orphaned_metadata": len(orphaned_metadata),
            "created_metadata": [],
            "removed_metadata": []
        }
        
        # Create metadata for images without it
        for filename in missing_metadata:
            try:
                image_path = self._get_image_path(filename)
                from PIL import Image
                
                with Image.open(image_path) as img:
                    width, height = img.size
                
                image_data = {
                    "filename": filename,
                    "original_name": filename,
                    "width": width,
                    "height": height
                }
                
                image_id = self.add_image(image_data)
                results["created_metadata"].append({"filename": filename, "id": image_id})
                
            except Exception as e:
                print(f"Error creating metadata for {filename}: {e}")
        
        # Remove orphaned metadata
        for filename in orphaned_metadata:
            try:
                meta_path = self._get_meta_path(filename)
                thumb_path = self._get_thumb_path(filename)
                
                if meta_path.exists():
                    meta_path.unlink()
                if thumb_path.exists():
                    thumb_path.unlink()
                
                results["removed_metadata"].append(filename)
                
            except Exception as e:
                print(f"Error removing orphaned metadata for {filename}: {e}")
        
        return results
    
    def get_images_in_gallery(self, gallery_id: str) -> List[Dict[str, Any]]:
        """Get all images that belong to a specific gallery"""
        all_images = self.get_all_images()
        return [img for img in all_images if gallery_id in img.get("galleries", [])]
    
    def add_image_to_gallery(self, image_id: str, gallery_id: str) -> bool:
        """Add an image to a gallery"""
        image = self.get_image_by_id(image_id)
        if not image:
            return False
        
        galleries = image.get("galleries", [])
        if gallery_id not in galleries:
            galleries.append(gallery_id)
            return self.update_image(image_id, {"galleries": galleries})
        
        return True  # Already in gallery
    
    def remove_image_from_gallery(self, image_id: str, gallery_id: str) -> bool:
        """Remove an image from a gallery"""
        image = self.get_image_by_id(image_id)
        if not image:
            return False
        
        galleries = image.get("galleries", [])
        if gallery_id in galleries:
            galleries.remove(gallery_id)
            return self.update_image(image_id, {"galleries": galleries})
        
        return True  # Already not in gallery
    
    def get_thumbnail_url(self, filename: str, base_url: str) -> str:
        """Get the URL for an image's thumbnail"""
        thumb_filename = Path(filename).stem + ".thumb.jpg"
        return f"{base_url}/api/channels/com.epaperframe.photoframe/assets/uploads/{thumb_filename}"
