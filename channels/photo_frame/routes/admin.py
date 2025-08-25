"""
Administrative routes for Photo Frame Channel

Handles all administrative and maintenance endpoints including:
- Database rebuilding and maintenance
- Thumbnail regeneration and processing
- Filesystem synchronization
- System health checks and diagnostics
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

# Import dependencies that will be injected
from ..services import ImageService, GalleryService, StorageService, RenderingService
from ..models import SettingsManager


class AdminRoutes:
    """Administrative routes class with dependency injection"""
    
    def __init__(self, image_service: ImageService, gallery_service: GalleryService,
                 storage_service: StorageService, rendering_service: RenderingService,
                 settings_manager: SettingsManager, metadata_manager):
        self.image_service = image_service
        self.gallery_service = gallery_service
        self.storage_service = storage_service
        self.rendering_service = rendering_service
        self.settings_manager = settings_manager
        self.metadata = metadata_manager
        
    def create_router(self) -> APIRouter:
        """Create and configure the admin router"""
        router = APIRouter(prefix="/admin", tags=["administration"])
        
        @router.post("/regenerate-thumbnails")
        async def regenerate_thumbnails():
            """Regenerate thumbnails for all existing images"""
            try:
                # Use the new image service for thumbnail regeneration
                result = await self.image_service.regenerate_thumbnails()
                
                return JSONResponse({
                    "success": True,
                    "thumbnails_generated": result.get("regenerated_count", 0),
                    "errors": result.get("errors", []),
                    "total_processed": result.get("total_processed", 0)
                })
                
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to regenerate thumbnails: {str(e)}"
                )

        @router.post("/rebuild-database")
        async def rebuild_database():
            """Rebuild database from existing files in uploads directory"""
            try:
                # Use the storage service for database rebuilding
                result = await self.storage_service.rebuild_database_from_filesystem()
                
                return JSONResponse({
                    "success": True,
                    "images_added": result.get("images_added", 0),
                    "images_updated": result.get("images_updated", 0),
                    "images_removed": result.get("images_removed", 0),
                    "errors": result.get("errors", [])
                })
                
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to rebuild database: {str(e)}"
                )

        @router.post("/sync-filesystem")
        async def sync_filesystem():
            """Sync metadata files with filesystem state"""
            try:
                # Use the image service for filesystem synchronization
                results = await self.image_service.sync_filesystem()
                
                return JSONResponse({
                    "success": True,
                    "files_synced": results.get("files_synced", 0),
                    "metadata_created": results.get("metadata_created", 0),
                    "metadata_updated": results.get("metadata_updated", 0),
                    "orphaned_removed": results.get("orphaned_removed", 0),
                    "errors": results.get("errors", [])
                })
                
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to sync filesystem: {str(e)}"
                )

        @router.post("/cleanup-orphaned-files")
        async def cleanup_orphaned_files():
            """Remove orphaned files that are no longer referenced"""
            try:
                result = await self.storage_service.cleanup_orphaned_files()
                
                return JSONResponse({
                    "success": True,
                    "files_removed": result.get("files_removed", 0),
                    "space_freed_mb": result.get("space_freed_mb", 0),
                    "errors": result.get("errors", [])
                })
                
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to cleanup orphaned files: {str(e)}"
                )

        @router.post("/validate-integrity")
        async def validate_data_integrity():
            """Validate data integrity across all services"""
            try:
                # Validate gallery data integrity
                gallery_validation = await self.gallery_service.validate_galleries_data_integrity()
                
                # Validate storage integrity  
                storage_validation = await self.storage_service.validate_galleries_integrity()
                
                # Check for missing thumbnails
                thumbnail_validation = await self.image_service.validate_thumbnails()
                
                return JSONResponse({
                    "success": True,
                    "gallery_integrity": gallery_validation,
                    "storage_integrity": storage_validation,
                    "thumbnail_integrity": thumbnail_validation,
                    "overall_status": "healthy" if all([
                        gallery_validation.get("valid", False),
                        storage_validation.get("valid", False),
                        thumbnail_validation.get("valid", False)
                    ]) else "issues_found"
                })
                
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Integrity validation failed: {str(e)}"
                )

        @router.get("/system-status")
        async def get_system_status():
            """Get overall system health and statistics"""
            try:
                # Get statistics from all services
                galleries = await self.gallery_service.list_galleries()
                
                # Count images across all galleries
                total_images = 0
                for gallery in galleries:
                    total_images += len(gallery.content_ids)
                
                # Get storage statistics
                storage_stats = await self.storage_service.get_storage_statistics()
                
                return JSONResponse({
                    "success": True,
                    "statistics": {
                        "total_galleries": len(galleries),
                        "total_images": total_images,
                        "storage_used_mb": storage_stats.get("used_mb", 0),
                        "thumbnail_count": storage_stats.get("thumbnail_count", 0),
                        "last_sync": storage_stats.get("last_sync"),
                        "health_status": "healthy"
                    },
                    "services_status": {
                        "gallery_service": "active",
                        "image_service": "active", 
                        "storage_service": "active",
                        "rendering_service": "active"
                    }
                })
                
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to get system status: {str(e)}"
                )

        @router.post("/clear-cache")
        async def clear_cache():
            """Clear all caches (rendering, thumbnails, etc.)"""
            try:
                # Clear rendering cache
                await self.rendering_service.clear_cache()
                
                return JSONResponse({
                    "success": True,
                    "message": "All caches cleared successfully"
                })
                
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to clear cache: {str(e)}"
                )
        
        return router


# Factory function for creating router with dependencies
def create_admin_router(image_service: ImageService, gallery_service: GalleryService,
                       storage_service: StorageService, rendering_service: RenderingService,
                       settings_manager: SettingsManager, metadata_manager) -> APIRouter:
    """Factory function to create admin router with injected dependencies"""
    routes = AdminRoutes(
        image_service, gallery_service, storage_service, 
        rendering_service, settings_manager, metadata_manager
    )
    return routes.create_router()


# Default router for backward compatibility (will be created in main channel)
router = APIRouter(prefix="/admin", tags=["administration"])
