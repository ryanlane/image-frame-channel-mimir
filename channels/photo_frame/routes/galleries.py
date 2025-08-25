"""
Gallery management routes for Photo Frame Channel

Handles all gallery-related endpoints including:
- Gallery creation, listing, and management
- Gallery image assignment and removal
- Gallery settings and metadata
- Gallery-specific image operations
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

# Import dependencies that will be injected
# Use absolute imports to avoid relative import issues
try:
    from services import GalleryService, ImageService, StorageService
    from models import Gallery, GalleryCreate, GalleryUpdate
except ImportError:
    # Fallback for when running from channel directory
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from services import GalleryService, ImageService, StorageService
    from models import Gallery, GalleryCreate, GalleryUpdate


class GalleryRoutes:
    """Gallery routes class with dependency injection"""
    
    def __init__(self, gallery_service: GalleryService, image_service: ImageService,
                 storage_service: StorageService):
        self.gallery_service = gallery_service
        self.image_service = image_service
        self.storage_service = storage_service
        
    def create_router(self) -> APIRouter:
        """Create and configure the galleries router"""
        router = APIRouter(prefix="/galleries", tags=["galleries"])
        
        @router.get("")
        async def list_galleries():
            """List all galleries"""
            try:
                galleries = await self.gallery_service.list_galleries()
                
                return JSONResponse([
                    {
                        "id": gallery.id,
                        "name": gallery.name,
                        "description": gallery.description,
                        "image_count": len(gallery.content_ids),
                        "settings": gallery.settings,
                        "created_at": gallery.created_at.isoformat() if gallery.created_at else None,
                        "updated_at": gallery.updated_at.isoformat() if gallery.updated_at else None
                    }
                    for gallery in galleries
                ])
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to list galleries: {str(e)}")

        @router.post("")
        async def create_gallery(request: Request):
            """Create a new gallery"""
            try:
                data = await request.json()
                
                # Validate gallery data
                gallery_data = GalleryCreate(**data)
                
                # Create gallery using service
                gallery = await self.gallery_service.create_gallery(gallery_data)
                
                return JSONResponse({
                    "success": True,
                    "gallery": {
                        "id": gallery.id,
                        "name": gallery.name,
                        "description": gallery.description,
                        "created_at": gallery.created_at.isoformat() if gallery.created_at else None
                    }
                })
                
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Gallery creation failed: {str(e)}")

        @router.get("/{gallery_id}")
        async def get_gallery(gallery_id: str):
            """Get a specific gallery with its images"""
            try:
                gallery = await self.gallery_service.get_gallery(gallery_id)
                
                if not gallery:
                    raise HTTPException(status_code=404, detail="Gallery not found")
                
                return JSONResponse({
                    "id": gallery.id,
                    "name": gallery.name,
                    "description": gallery.description,
                    "content_ids": gallery.content_ids,
                    "image_count": len(gallery.content_ids),
                    "settings": gallery.settings,
                    "created_at": gallery.created_at.isoformat() if gallery.created_at else None,
                    "updated_at": gallery.updated_at.isoformat() if gallery.updated_at else None
                })
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get gallery: {str(e)}")

        @router.put("/{gallery_id}")
        async def update_gallery(gallery_id: str, request: Request):
            """Update a gallery's metadata"""
            try:
                data = await request.json()
                
                # Validate update data
                update_data = GalleryUpdate(**data)
                
                # Update gallery using service
                gallery = await self.gallery_service.update_gallery(gallery_id, update_data)
                
                if not gallery:
                    raise HTTPException(status_code=404, detail="Gallery not found")
                
                return JSONResponse({
                    "success": True,
                    "gallery": {
                        "id": gallery.id,
                        "name": gallery.name,
                        "description": gallery.description,
                        "updated_at": gallery.updated_at.isoformat() if gallery.updated_at else None
                    }
                })
                
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Gallery update failed: {str(e)}")

        @router.delete("/{gallery_id}")
        async def delete_gallery(gallery_id: str):
            """Delete a gallery (images remain in system)"""
            try:
                success = await self.gallery_service.delete_gallery(gallery_id)
                
                if not success:
                    raise HTTPException(status_code=404, detail="Gallery not found")
                
                return JSONResponse({"success": True})
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Gallery deletion failed: {str(e)}")

        @router.post("/{gallery_id}/images")
        async def assign_images_to_gallery(gallery_id: str, request: Request):
            """Assign images to a gallery"""
            try:
                data = await request.json()
                image_ids = data.get("image_ids", [])
                
                if not image_ids:
                    raise HTTPException(status_code=400, detail="image_ids array required")
                
                # Assign images using service
                result = await self.gallery_service.assign_images_to_gallery(gallery_id, image_ids)
                
                return JSONResponse({
                    "success": True,
                    "assigned_count": result.get("assigned_count", 0),
                    "already_assigned": result.get("already_assigned", []),
                    "not_found": result.get("not_found", [])
                })
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Image assignment failed: {str(e)}")

        @router.delete("/{gallery_id}/images/{image_id}")
        async def remove_image_from_gallery(gallery_id: str, image_id: str):
            """Remove an image from a gallery"""
            try:
                success = await self.gallery_service.remove_image_from_gallery(gallery_id, image_id)
                
                if not success:
                    raise HTTPException(status_code=404, detail="Gallery or image not found")
                
                return JSONResponse({"success": True})
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Image removal failed: {str(e)}")

        @router.post("/{gallery_id}/images/reorder")
        async def reorder_gallery_images(gallery_id: str, request: Request):
            """Reorder images within a gallery"""
            try:
                data = await request.json()
                image_ids = data.get("image_ids", [])
                
                if not image_ids:
                    raise HTTPException(status_code=400, detail="image_ids array required")
                
                # Reorder images using service
                await self.gallery_service.reorder_gallery_images(gallery_id, image_ids)
                
                return JSONResponse({"success": True})
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Image reorder failed: {str(e)}")
        
        return router


# Factory function for creating router with dependencies
def create_galleries_router(gallery_service: GalleryService, image_service: ImageService,
                           storage_service: StorageService) -> APIRouter:
    """Factory function to create galleries router with injected dependencies"""
    routes = GalleryRoutes(gallery_service, image_service, storage_service)
    return routes.create_router()


# Default router for backward compatibility (will be created in main channel)
router = APIRouter(prefix="/galleries", tags=["galleries"])
