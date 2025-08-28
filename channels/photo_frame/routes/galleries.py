"""
Gallery management routes for Photo Frame Channel

⚠️ API INTEGRATION: These routes are mounted under /api/channels/com.epaperframe.photoframe/
Handles all gallery-related endpoints including:
- Gallery creation, listing, and management (/subchannels)
- Gallery image assignment and removal (/subchannels/{id}/content)
- Gallery settings and metadata (/subchannels/{id}/settings)
- Gallery-specific image operations (/subchannels/{id}/images)

IMPORTANT: All routes must be compatible with the main API structure.
The main API expects these endpoints:
- GET /api/channels/{channel_id}/subchannels
- POST /api/channels/{channel_id}/subchannels
- GET /api/channels/{channel_id}/subchannels/{subchannel_id}
- PUT /api/channels/{channel_id}/subchannels/{subchannel_id}
- DELETE /api/channels/{channel_id}/subchannels/{subchannel_id}
- POST /api/channels/{channel_id}/subchannels/{subchannel_id}/content
- GET /api/channels/{channel_id}/subchannels/{subchannel_id}/images
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
        """
        Create and configure the galleries router for API integration
        
        IMPORTANT: Uses /subchannels prefix to match main API expectations
        When mounted under /api/channels/com.epaperframe.photoframe/, this creates:
        - /api/channels/com.epaperframe.photoframe/subchannels/
        """
        router = APIRouter(prefix="/subchannels", tags=["subchannels"])
        
        @router.get("")
        async def list_galleries():
            """List all galleries"""
            try:
                galleries = self.gallery_service.get_all_galleries()
                
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

        @router.post("/{gallery_id}/content")
        async def assign_content_to_subchannel(gallery_id: str, request: Request):
            """
            Assign content (images) to a subchannel (gallery)
            
            Expected by main API at: POST /api/channels/{channel_id}/subchannels/{subchannel_id}/content
            
            Body:
            {
                "contentIds": ["1", "2", "3"],
                "action": "add"  // "add", "remove", or "replace"
            }
            """
            try:
                data = await request.json()
                content_ids = data.get("contentIds", [])
                action = data.get("action", "add")
                
                if not content_ids:
                    raise HTTPException(status_code=400, detail="contentIds array required")
                
                if action not in ["add", "remove", "replace"]:
                    raise HTTPException(status_code=400, detail="action must be 'add', 'remove', or 'replace'")
                
                # Use the gallery service to assign content
                if action == "add":
                    result = self.gallery_service.assign_images_to_gallery(
                        gallery_id, content_ids, all_image_ids=set(content_ids)
                    )
                elif action == "remove":
                    result = self.gallery_service.remove_images_from_gallery(gallery_id, content_ids)
                else:  # replace
                    result = self.gallery_service.replace_gallery_images(gallery_id, content_ids)
                
                return JSONResponse({
                    "success": True,
                    "action": action,
                    "content_ids": content_ids,
                    "result": result
                })
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Content assignment failed: {str(e)}")

        @router.get("/{gallery_id}/images")
        async def get_subchannel_images(gallery_id: str):
            """
            Get images from a specific subchannel (gallery)
            
            Expected by main API at: GET /api/channels/{channel_id}/subchannels/{subchannel_id}/images
            """
            try:
                gallery = self.gallery_service.get_gallery(gallery_id)
                if not gallery:
                    raise HTTPException(status_code=404, detail="Gallery not found")
                
                # Get all images and filter by gallery content
                all_images = self.image_service.get_all_images()
                gallery_images = [
                    img for img in all_images 
                    if str(img.get("id")) in gallery.content_ids
                ]
                
                return JSONResponse({
                    "images": gallery_images,
                    "total": len(gallery_images),
                    "gallery_id": gallery_id,
                    "gallery_name": gallery.name
                })
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get gallery images: {str(e)}")

        @router.post("/{gallery_id}/images")
        async def assign_images_to_gallery(gallery_id: str, request: Request):
            """Assign images to a gallery (legacy endpoint - use /content instead)"""
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

        @router.get("/{gallery_id}/images/{image_id}/thumbnail")
        async def get_subchannel_image_thumbnail(gallery_id: str, image_id: str):
            """
            Get thumbnail for a specific image in a subchannel
            
            Expected by main API at: GET /api/channels/{channel_id}/subchannels/{subchannel_id}/images/{image_id}/thumbnail
            
            This is a critical endpoint for the main API integration!
            """
            try:
                # Verify gallery exists
                gallery = self.gallery_service.get_gallery(gallery_id)
                if not gallery:
                    raise HTTPException(status_code=404, detail="Gallery not found")
                
                # Verify image is in this gallery
                if str(image_id) not in gallery.content_ids:
                    raise HTTPException(status_code=404, detail="Image not found in this gallery")
                
                # Get image metadata to find filename
                all_images = self.image_service.get_all_images()
                image = next((img for img in all_images if str(img.get("id")) == str(image_id)), None)
                
                if not image:
                    raise HTTPException(status_code=404, detail="Image not found")
                
                filename = image.get("filename")
                if not filename:
                    raise HTTPException(status_code=404, detail="Image filename not found")
                
                # Generate thumbnail filename: image.jpg -> image.thumb.jpg
                name_stem = Path(filename).stem
                thumb_filename = f"{name_stem}.thumb.jpg"
                thumb_path = self.storage_service.channel_dir / "assets" / "uploads" / thumb_filename
                
                # Check if thumbnail exists, generate if needed
                if not thumb_path.exists():
                    original_path = self.storage_service.channel_dir / "assets" / "uploads" / filename
                    if original_path.exists():
                        # Generate thumbnail using storage service
                        await self.storage_service.ensure_thumbnail_exists(str(original_path))
                    
                    # Check again after generation
                    if not thumb_path.exists():
                        raise HTTPException(status_code=404, detail="Thumbnail not available")
                
                # Serve the thumbnail
                from fastapi.responses import FileResponse
                return FileResponse(
                    path=str(thumb_path),
                    media_type="image/jpeg",
                    headers={
                        "Cache-Control": "public, max-age=3600",
                        "X-Gallery-ID": gallery_id,
                        "X-Image-ID": image_id
                    }
                )
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Thumbnail serving failed: {str(e)}")

        # Note: Image reordering is handled by the subchannel settings router
        # at /subchannels/{subchannel_id}/images/reorder
        
        return router


# Factory function for creating router with dependencies
def create_galleries_router(gallery_service: GalleryService, image_service: ImageService,
                           storage_service: StorageService) -> APIRouter:
    """Factory function to create galleries router with injected dependencies"""
    routes = GalleryRoutes(gallery_service, image_service, storage_service)
    return routes.create_router()


# Default router for backward compatibility (will be created in main channel)
router = APIRouter(prefix="/galleries", tags=["galleries"])
