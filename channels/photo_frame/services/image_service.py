"""
Image Service - Business logic for image operations
"""

import hashlib
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ..models import Image, ImageMetadata, ImageUploadResult, ImageBatchUploadResult


class ImageService:
    """Service for managing image operations"""
    
    def __init__(self, channel_dir: Path, metadata_manager, image_processor=None):
        self.channel_dir = Path(channel_dir)
        self.uploads_dir = self.channel_dir / "assets" / "uploads"
        self.metadata = metadata_manager
        self.image_processor = image_processor
        
        # Ensure directories exist
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
    
    def get_all_images(self) -> List[Dict[str, Any]]:
        """Get all images with metadata"""
        return self.metadata.get_all_images()
    
    def get_image_by_id(self, image_id: str) -> Optional[Dict[str, Any]]:
        """Get image by ID"""
        return self.metadata.get_image_by_id(image_id)
    
    def get_enabled_images(self) -> List[Dict[str, Any]]:
        """Get all enabled images"""
        all_images = self.get_all_images()
        return [img for img in all_images if img.get("enabled", True)]
    
    def upload_files(self, files: List[Any]) -> ImageBatchUploadResult:
        """
        Upload multiple image files
        
        Args:
            files: List of uploaded file objects
            
        Returns:
            ImageBatchUploadResult with individual upload results
        """
        batch_result = ImageBatchUploadResult()
        
        for file in files:
            result = self._upload_single_file(file)
            batch_result.add_result(result)
        
        return batch_result
    
    def _upload_single_file(self, file) -> ImageUploadResult:
        """Upload a single image file"""
        try:
            # Validate file type
            if not self._is_valid_image_file(file.filename):
                return ImageUploadResult(
                    success=False,
                    filename=file.filename,
                    error="Invalid file type. Only image files are allowed."
                )
            
            # Generate unique filename
            filename = self._generate_unique_filename(file.filename)
            file_path = self.uploads_dir / filename
            
            # Save file
            with open(file_path, "wb") as f:
                content = file.file.read()
                f.write(content)
            
            # Extract metadata and save to database
            image_id = self._process_uploaded_image(file_path, filename)
            
            return ImageUploadResult(
                success=True,
                image_id=image_id,
                filename=filename
            )
            
        except Exception as e:
            return ImageUploadResult(
                success=False,
                filename=getattr(file, 'filename', 'unknown'),
                error=str(e)
            )
    
    def _is_valid_image_file(self, filename: str) -> bool:
        """Check if file is a valid image"""
        if not filename:
            return False
        
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        extension = Path(filename).suffix.lower()
        return extension in valid_extensions
    
    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate unique filename to avoid conflicts"""
        base_path = self.uploads_dir / original_filename
        
        if not base_path.exists():
            return original_filename
        
        # Add timestamp suffix
        name_stem = Path(original_filename).stem
        extension = Path(original_filename).suffix
        timestamp = int(datetime.now().timestamp())
        
        return f"{name_stem}_{timestamp}{extension}"
    
    def _process_uploaded_image(self, file_path: Path, filename: str) -> str:
        """Process uploaded image and extract metadata"""
        try:
            # Get image info
            if self.image_processor:
                image_info = self.image_processor.get_image_info(file_path)
            else:
                # Basic fallback
                image_info = {
                    "width": 0,
                    "height": 0,
                    "format": Path(filename).suffix.lower().lstrip('.').upper()
                }
            
            # Generate thumbnail
            if self.image_processor:
                self.image_processor.generate_thumbnail(file_path)
            
            # Create metadata record
            file_stats = file_path.stat()
            image_data = {
                "filename": filename,
                "file_size": file_stats.st_size,
                "width": image_info.get("width", 0),
                "height": image_info.get("height", 0),
                "format": image_info.get("format", ""),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "modified_at": datetime.now(timezone.utc).isoformat(),
                "enabled": True,
                "times_shown": 0,
                "last_shown": None,
                "sort_order": 0,
                "crop_x": 0,
                "crop_y": 0,
                "crop_width": 100,
                "crop_height": 100,
                "tags": [],
                "description": ""
            }
            
            # Save to metadata
            image_id = self.metadata.add_image(image_data)
            return str(image_id)
            
        except Exception as e:
            # Clean up file on error
            if file_path.exists():
                file_path.unlink()
            raise e
    
    def update_image(self, image_id: str, update_data: Dict[str, Any]) -> bool:
        """Update image metadata"""
        image = self.get_image_by_id(image_id)
        if not image:
            raise ValueError(f"Image '{image_id}' not found")
        
        # Validate crop parameters if provided
        if any(key in update_data for key in ['crop_x', 'crop_y', 'crop_width', 'crop_height']):
            self._validate_crop_parameters(update_data)
        
        # Update metadata
        success = self.metadata.update_image(image_id, update_data)
        
        return success
    
    def _validate_crop_parameters(self, crop_data: Dict[str, Any]) -> None:
        """Validate crop parameters"""
        for param in ['crop_x', 'crop_y']:
            if param in crop_data:
                value = crop_data[param]
                if not isinstance(value, (int, float)) or value < 0 or value > 100:
                    raise ValueError(f"{param} must be between 0 and 100")
        
        for param in ['crop_width', 'crop_height']:
            if param in crop_data:
                value = crop_data[param]
                if not isinstance(value, (int, float)) or value <= 0 or value > 100:
                    raise ValueError(f"{param} must be between 0 and 100")
    
    def toggle_image(self, image_id: str) -> bool:
        """Toggle image enabled state"""
        image = self.get_image_by_id(image_id)
        if not image:
            raise ValueError(f"Image '{image_id}' not found")
        
        new_enabled_state = not image.get("enabled", True)
        success = self.metadata.update_image(image_id, {"enabled": new_enabled_state})
        
        return new_enabled_state if success else image.get("enabled", True)
    
    def delete_image(self, image_id: str) -> bool:
        """Delete image file and metadata"""
        image = self.get_image_by_id(image_id)
        if not image:
            raise ValueError(f"Image '{image_id}' not found")
        
        filename = image["filename"]
        file_path = self.uploads_dir / filename
        
        try:
            # Delete thumbnail if it exists
            if self.image_processor:
                name_stem = Path(filename).stem
                thumbnail_path = self.uploads_dir / f"{name_stem}.thumb.jpg"
                if thumbnail_path.exists():
                    thumbnail_path.unlink()
            
            # Delete main image file
            if file_path.exists():
                file_path.unlink()
            
            # Remove from metadata
            success = self.metadata.delete_image(image_id)
            
            return success
            
        except Exception as e:
            print(f"Error deleting image {image_id}: {e}")
            return False
    
    def update_image_stats(self, image_id: str, times_shown: int = None) -> bool:
        """Update image display statistics"""
        image = self.get_image_by_id(image_id)
        if not image:
            return False
        
        if times_shown is not None:
            new_times_shown = times_shown
        else:
            new_times_shown = image.get("times_shown", 0) + 1
        
        update_data = {
            "times_shown": new_times_shown,
            "last_shown": datetime.now(timezone.utc).isoformat()
        }
        
        return self.metadata.update_image(image_id, update_data)
    
    def get_image_file_path(self, filename: str) -> Path:
        """Get full path to image file"""
        return self.uploads_dir / filename
    
    def get_thumbnail_path(self, filename: str) -> Path:
        """Get path to thumbnail file"""
        name_stem = Path(filename).stem
        thumbnail_filename = f"{name_stem}.thumb.jpg"
        return self.uploads_dir / thumbnail_filename
    
    def file_exists(self, filename: str) -> bool:
        """Check if image file exists"""
        return self.get_image_file_path(filename).exists()
    
    def thumbnail_exists(self, filename: str) -> bool:
        """Check if thumbnail file exists"""
        return self.get_thumbnail_path(filename).exists()
    
    def regenerate_thumbnails(self) -> Dict[str, Any]:
        """Regenerate thumbnails for all images"""
        if not self.image_processor:
            return {"error": "Image processor not available"}
        
        all_images = self.get_all_images()
        generated_count = 0
        error_count = 0
        errors = []
        
        for image in all_images:
            filename = image["filename"]
            source_path = self.get_image_file_path(filename)
            
            if source_path.exists():
                try:
                    self.image_processor.generate_thumbnail(source_path)
                    generated_count += 1
                    print(f"Generated thumbnail: {filename}")
                    
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
    
    def sync_filesystem(self) -> Dict[str, Any]:
        """Sync database with filesystem"""
        if not self.uploads_dir.exists():
            return {"error": "Uploads directory does not exist"}
        
        # Get all image files from uploads directory
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        file_count = 0
        
        for file_path in self.uploads_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                # Skip thumbnail files
                if '.thumb.' in file_path.name:
                    continue
                
                # Check if already in database
                existing_images = self.get_all_images()
                found = any(img["filename"] == file_path.name for img in existing_images)
                
                if not found:
                    try:
                        # Add to database
                        self._process_uploaded_image(file_path, file_path.name)
                        file_count += 1
                        print(f"Added to database: {file_path.name}")
                    except Exception as e:
                        print(f"Error processing {file_path.name}: {e}")
        
        return {
            "files_added": file_count,
            "message": f"Added {file_count} files to database"
        }
    
    def get_storage_usage(self) -> Dict[str, Any]:
        """Calculate storage usage"""
        def dir_size(path: Path) -> int:
            if not path.exists():
                return 0
            return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        
        uploads_size = dir_size(self.uploads_dir)
        
        return {
            "uploads_mb": round(uploads_size / 1024 / 1024, 2),
            "total_mb": round(uploads_size / 1024 / 1024, 2),
            "total_files": len(list(self.uploads_dir.glob('*'))) if self.uploads_dir.exists() else 0
        }
    
    def validate_image_integrity(self) -> Dict[str, Any]:
        """Validate that all database images have corresponding files"""
        all_images = self.get_all_images()
        missing_files = []
        valid_files = 0
        
        for image in all_images:
            filename = image["filename"]
            if not self.file_exists(filename):
                missing_files.append({
                    "id": image["id"],
                    "filename": filename
                })
            else:
                valid_files += 1
        
        return {
            "total_images": len(all_images),
            "valid_files": valid_files,
            "missing_files": len(missing_files),
            "missing_file_details": missing_files
        }
