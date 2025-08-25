"""
Storage Service - Business logic for file storage and management
"""

import shutil
from pathlib import Path
from typing import Dict, Any, Optional


class StorageService:
    """Service for managing file storage operations"""
    
    def __init__(self, channel_dir: Path):
        self.channel_dir = Path(channel_dir)
        self.uploads_dir = self.channel_dir / "assets" / "uploads"
        self.data_dir = self.channel_dir / "data"
        self.current_dir = self.channel_dir / "current"
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Create necessary directories"""
        dirs = [
            self.uploads_dir,
            self.data_dir,
            self.current_dir,
            self.data_dir / "thumbs"  # Legacy thumbnail directory
        ]
        
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def get_file_path(self, filename: str, file_type: str = "upload") -> Path:
        """
        Get full path for a file based on type
        
        Args:
            filename: Name of the file
            file_type: Type of file ('upload', 'thumbnail', 'current', 'data')
        """
        if file_type == "upload":
            return self.uploads_dir / filename
        elif file_type == "thumbnail":
            return self.uploads_dir / filename  # Co-located thumbnails
        elif file_type == "current":
            return self.current_dir / filename
        elif file_type == "data":
            return self.data_dir / filename
        else:
            raise ValueError(f"Unknown file type: {file_type}")
    
    def file_exists(self, filename: str, file_type: str = "upload") -> bool:
        """Check if file exists"""
        file_path = self.get_file_path(filename, file_type)
        return file_path.exists()
    
    def get_file_info(self, filename: str, file_type: str = "upload") -> Optional[Dict[str, Any]]:
        """Get file information"""
        file_path = self.get_file_path(filename, file_type)
        
        if not file_path.exists():
            return None
        
        try:
            stat = file_path.stat()
            return {
                "filename": filename,
                "path": str(file_path),
                "size": stat.st_size,
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "exists": True
            }
        except Exception as e:
            return {
                "filename": filename,
                "path": str(file_path),
                "exists": False,
                "error": str(e)
            }
    
    def delete_file(self, filename: str, file_type: str = "upload") -> bool:
        """Delete a file"""
        try:
            file_path = self.get_file_path(filename, file_type)
            
            if file_path.exists():
                file_path.unlink()
                return True
            
            return False  # File didn't exist
            
        except Exception as e:
            print(f"Error deleting file {filename}: {e}")
            return False
    
    def copy_file(self, source_filename: str, dest_filename: str, 
                  source_type: str = "upload", dest_type: str = "upload") -> bool:
        """Copy a file from one location to another"""
        try:
            source_path = self.get_file_path(source_filename, source_type)
            dest_path = self.get_file_path(dest_filename, dest_type)
            
            if not source_path.exists():
                return False
            
            # Ensure destination directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(source_path, dest_path)
            return True
            
        except Exception as e:
            print(f"Error copying file {source_filename} to {dest_filename}: {e}")
            return False
    
    def move_file(self, source_filename: str, dest_filename: str,
                  source_type: str = "upload", dest_type: str = "upload") -> bool:
        """Move a file from one location to another"""
        try:
            source_path = self.get_file_path(source_filename, source_type)
            dest_path = self.get_file_path(dest_filename, dest_type)
            
            if not source_path.exists():
                return False
            
            # Ensure destination directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(source_path), str(dest_path))
            return True
            
        except Exception as e:
            print(f"Error moving file {source_filename} to {dest_filename}: {e}")
            return False
    
    def get_directory_size(self, directory_type: str = "uploads") -> Dict[str, Any]:
        """Get size information for a directory"""
        try:
            if directory_type == "uploads":
                directory = self.uploads_dir
            elif directory_type == "data":
                directory = self.data_dir
            elif directory_type == "current":
                directory = self.current_dir
            else:
                raise ValueError(f"Unknown directory type: {directory_type}")
            
            if not directory.exists():
                return {
                    "directory": str(directory),
                    "exists": False,
                    "total_size": 0,
                    "total_files": 0
                }
            
            total_size = 0
            total_files = 0
            
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    total_files += 1
                    total_size += file_path.stat().st_size
            
            return {
                "directory": str(directory),
                "exists": True,
                "total_size": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "total_files": total_files
            }
            
        except Exception as e:
            return {
                "directory": directory_type,
                "exists": False,
                "error": str(e)
            }
    
    def get_storage_summary(self) -> Dict[str, Any]:
        """Get summary of all storage usage"""
        uploads_info = self.get_directory_size("uploads")
        data_info = self.get_directory_size("data")
        current_info = self.get_directory_size("current")
        
        total_size = (
            uploads_info.get("total_size", 0) + 
            data_info.get("total_size", 0) + 
            current_info.get("total_size", 0)
        )
        
        total_files = (
            uploads_info.get("total_files", 0) + 
            data_info.get("total_files", 0) + 
            current_info.get("total_files", 0)
        )
        
        return {
            "uploads": uploads_info,
            "data": data_info,
            "current": current_info,
            "total_size": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "total_files": total_files
        }
    
    def cleanup_orphaned_files(self, valid_filenames: set) -> Dict[str, Any]:
        """Clean up files that are not referenced in the database"""
        try:
            if not self.uploads_dir.exists():
                return {"error": "Uploads directory does not exist"}
            
            deleted_files = []
            deleted_size = 0
            
            for file_path in self.uploads_dir.iterdir():
                if file_path.is_file():
                    # Skip thumbnail files (they're managed separately)
                    if '.thumb.' in file_path.name:
                        continue
                    
                    # Check if file is referenced
                    if file_path.name not in valid_filenames:
                        try:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            deleted_files.append(file_path.name)
                            deleted_size += file_size
                        except Exception as e:
                            print(f"Error deleting orphaned file {file_path.name}: {e}")
            
            return {
                "deleted_files": len(deleted_files),
                "deleted_size_mb": round(deleted_size / 1024 / 1024, 2),
                "files": deleted_files
            }
            
        except Exception as e:
            return {"error": f"Failed to cleanup orphaned files: {e}"}
    
    def cleanup_thumbnails(self, valid_filenames: set) -> Dict[str, Any]:
        """Clean up thumbnail files that don't have corresponding source images"""
        try:
            if not self.uploads_dir.exists():
                return {"error": "Uploads directory does not exist"}
            
            deleted_thumbnails = []
            deleted_size = 0
            
            # Find all thumbnail files
            for file_path in self.uploads_dir.iterdir():
                if file_path.is_file() and '.thumb.' in file_path.name:
                    # Extract original filename
                    thumbnail_name = file_path.name
                    # Remove .thumb.jpg to get original name stem
                    original_stem = thumbnail_name.replace('.thumb.jpg', '')
                    
                    # Check if any valid filename starts with this stem
                    has_source = any(
                        filename.startswith(original_stem) and '.thumb.' not in filename
                        for filename in valid_filenames
                    )
                    
                    if not has_source:
                        try:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            deleted_thumbnails.append(thumbnail_name)
                            deleted_size += file_size
                        except Exception as e:
                            print(f"Error deleting orphaned thumbnail {thumbnail_name}: {e}")
            
            return {
                "deleted_thumbnails": len(deleted_thumbnails),
                "deleted_size_mb": round(deleted_size / 1024 / 1024, 2),
                "thumbnails": deleted_thumbnails
            }
            
        except Exception as e:
            return {"error": f"Failed to cleanup thumbnails: {e}"}
    
    def backup_data(self, backup_dir: Path) -> Dict[str, Any]:
        """Create backup of important data files"""
        try:
            backup_dir = Path(backup_dir)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            backed_up_files = []
            
            # Backup galleries.json
            galleries_file = self.data_dir / "galleries.json"
            if galleries_file.exists():
                backup_path = backup_dir / "galleries.json"
                shutil.copy2(galleries_file, backup_path)
                backed_up_files.append("galleries.json")
            
            # Backup database file if it exists
            db_file = self.data_dir / "photo_frame.db"
            if db_file.exists():
                backup_path = backup_dir / "photo_frame.db"
                shutil.copy2(db_file, backup_path)
                backed_up_files.append("photo_frame.db")
            
            return {
                "success": True,
                "backup_dir": str(backup_dir),
                "backed_up_files": backed_up_files
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create backup: {e}"
            }
    
    def validate_storage_integrity(self) -> Dict[str, Any]:
        """Validate storage structure and permissions"""
        issues = []
        
        # Check directory existence and permissions
        required_dirs = [
            ("uploads", self.uploads_dir),
            ("data", self.data_dir),
            ("current", self.current_dir)
        ]
        
        for name, directory in required_dirs:
            if not directory.exists():
                issues.append(f"{name} directory missing: {directory}")
            elif not directory.is_dir():
                issues.append(f"{name} path is not a directory: {directory}")
            else:
                # Check write permissions
                try:
                    test_file = directory / ".write_test"
                    test_file.touch()
                    test_file.unlink()
                except Exception as e:
                    issues.append(f"{name} directory not writable: {e}")
        
        # Check available disk space
        try:
            statvfs = shutil.disk_usage(self.channel_dir)
            free_space_mb = statvfs.free / 1024 / 1024
            
            if free_space_mb < 100:  # Less than 100MB
                issues.append(f"Low disk space: {free_space_mb:.1f}MB available")
        except Exception as e:
            issues.append(f"Cannot check disk space: {e}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
