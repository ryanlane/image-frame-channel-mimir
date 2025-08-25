"""
Image Data Models for Photo Frame Channel
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pathlib import Path


class ImageMetadata:
    """Image metadata and statistics"""
    
    def __init__(self, image_data: Dict[str, Any]):
        self.id = str(image_data.get("id", ""))
        self.filename = image_data.get("filename", "")
        self.file_size = image_data.get("file_size", 0)
        self.width = image_data.get("width", 0)
        self.height = image_data.get("height", 0)
        self.format = image_data.get("format", "")
        self.created_at = image_data.get("created_at", "")
        self.modified_at = image_data.get("modified_at", "")
        self.enabled = image_data.get("enabled", True)
        self.times_shown = image_data.get("times_shown", 0)
        self.last_shown = image_data.get("last_shown")
        self.sort_order = image_data.get("sort_order", 0)
        
        # Crop settings
        self.crop_x = image_data.get("crop_x", 0)
        self.crop_y = image_data.get("crop_y", 0) 
        self.crop_width = image_data.get("crop_width", 100)
        self.crop_height = image_data.get("crop_height", 100)
        
        # Additional metadata
        self.tags = image_data.get("tags", [])
        self.description = image_data.get("description", "")

    @property
    def aspect_ratio(self) -> float:
        """Calculate image aspect ratio"""
        if self.height == 0:
            return 1.0
        return self.width / self.height

    @property
    def is_landscape(self) -> bool:
        """Check if image is landscape orientation"""
        return self.width > self.height

    @property
    def is_portrait(self) -> bool:
        """Check if image is portrait orientation"""
        return self.height > self.width

    @property
    def is_square(self) -> bool:
        """Check if image is square"""
        return self.width == self.height

    def get_thumbnail_filename(self) -> str:
        """Get thumbnail filename for this image"""
        name_stem = Path(self.filename).stem
        return f"{name_stem}.thumb.jpg"

    def update_stats(self, times_shown: Optional[int] = None) -> None:
        """Update display statistics"""
        if times_shown is not None:
            self.times_shown = times_shown
        else:
            self.times_shown += 1
        
        self.last_shown = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "filename": self.filename,
            "file_size": self.file_size,
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "enabled": self.enabled,
            "times_shown": self.times_shown,
            "last_shown": self.last_shown,
            "sort_order": self.sort_order,
            "crop_x": self.crop_x,
            "crop_y": self.crop_y,
            "crop_width": self.crop_width,
            "crop_height": self.crop_height,
            "tags": self.tags,
            "description": self.description,
            "aspect_ratio": self.aspect_ratio,
            "is_landscape": self.is_landscape,
            "is_portrait": self.is_portrait,
            "is_square": self.is_square
        }


class Image:
    """Image model for photo frame channel"""
    
    def __init__(self, metadata: ImageMetadata, file_path: Path):
        self.metadata = metadata
        self.file_path = file_path

    @property
    def id(self) -> str:
        return self.metadata.id

    @property
    def filename(self) -> str:
        return self.metadata.filename

    @property
    def enabled(self) -> bool:
        return self.metadata.enabled

    @property
    def exists(self) -> bool:
        """Check if image file exists on disk"""
        return self.file_path.exists()

    def get_thumbnail_path(self, uploads_dir: Path) -> Path:
        """Get path to thumbnail file"""
        thumbnail_filename = self.metadata.get_thumbnail_filename()
        return uploads_dir / thumbnail_filename

    def toggle_enabled(self) -> bool:
        """Toggle image enabled state"""
        self.metadata.enabled = not self.metadata.enabled
        return self.metadata.enabled

    def update_crop(self, crop_x: int, crop_y: int, crop_width: int, crop_height: int) -> None:
        """Update crop settings"""
        self.metadata.crop_x = crop_x
        self.metadata.crop_y = crop_y
        self.metadata.crop_width = crop_width
        self.metadata.crop_height = crop_height

    def update_sort_order(self, sort_order: int) -> None:
        """Update sort order"""
        self.metadata.sort_order = sort_order

    def record_display(self) -> None:
        """Record that this image was displayed"""
        self.metadata.update_stats()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = self.metadata.to_dict()
        data["exists"] = self.exists
        return data


class ImageUploadResult:
    """Result of image upload operation"""
    
    def __init__(self, success: bool, image_id: Optional[str] = None, 
                 filename: Optional[str] = None, error: Optional[str] = None):
        self.success = success
        self.image_id = image_id
        self.filename = filename
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "image_id": self.image_id,
            "filename": self.filename,
            "error": self.error
        }


class ImageBatchUploadResult:
    """Result of batch image upload operation"""
    
    def __init__(self):
        self.results: List[ImageUploadResult] = []
        self.total_files = 0
        self.successful_uploads = 0
        self.failed_uploads = 0

    def add_result(self, result: ImageUploadResult) -> None:
        """Add an upload result"""
        self.results.append(result)
        self.total_files += 1
        
        if result.success:
            self.successful_uploads += 1
        else:
            self.failed_uploads += 1

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if self.total_files == 0:
            return 0.0
        return (self.successful_uploads / self.total_files) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "results": [result.to_dict() for result in self.results],
            "total_files": self.total_files,
            "successful_uploads": self.successful_uploads,
            "failed_uploads": self.failed_uploads,
            "success_rate": self.success_rate
        }
