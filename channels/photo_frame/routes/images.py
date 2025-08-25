"""
Image management routes for Photo Frame Channel

Handles all image-related endpoints including:
- Image listing and metadata
- Image upload and processing
- Image updates, toggle, and deletion
- Image reordering within galleries
"""

from typing import List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse

# Import dependencies that will be injected  
# Use absolute imports to avoid relative import issues
try:
    from services import ImageService, GalleryService, StorageService
    from models import ImageUploadResult
except ImportError:
    # Fallback for when running from channel directory
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from services import ImageService, GalleryService, StorageService
    from models import ImageUploadResult


class ImageRoutes:
    """Image routes class with dependency injection"""
    
    def __init__(self, image_service: ImageService, gallery_service: GalleryService, 
                 storage_service: StorageService, metadata_manager, image_processor):
        self.image_service = image_service
        self.gallery_service = gallery_service
        self.storage_service = storage_service
        self.metadata = metadata_manager
        self.image_processor = image_processor
        
    def create_router(self) -> APIRouter:
        """Create and configure the images router"""
        router = APIRouter(prefix="/images", tags=["images"])
        
        @router.get("")
        async def list_images():
            """List all uploaded images with metadata"""
            try:
                images = self.metadata.get_all_images()
                return JSONResponse(images)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to list images: {str(e)}")

        @router.post("/upload")
        async def upload_images(files: List[UploadFile] = File(...)):
            """Handle image uploads with batch processing"""
            try:
                # Use the new image service for uploads
                result = self.image_service.upload_files(files)
                
                return JSONResponse({
                    "success": True,
                    "uploaded_count": result.successful_uploads,
                    "failed_count": result.failed_uploads,
                    "results": [
                        {
                            "filename": r.filename,
                            "success": r.success,
                            "image_id": r.image_id,
                            "error": r.error
                        }
                        for r in result.results
                    ]
                })
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

        @router.put("/{image_id}")
        async def update_image(
            image_id: str,
            title: str = Form(""),
            description: str = Form(""),
            crop_x: float = Form(0),
            crop_y: float = Form(0),
            crop_width: float = Form(100),
            crop_height: float = Form(100),
            preserve_aspect_ratio: bool = Form(False)
        ):
            """Update image metadata and crop settings"""
            try:
                updates = {
                    "title": title,
                    "description": description,
                    "crop_x": crop_x,
                    "crop_y": crop_y,
                    "crop_width": crop_width,
                    "crop_height": crop_height,
                    "preserve_aspect_ratio": preserve_aspect_ratio
                }
                
                success = self.metadata.update_image(image_id, updates)
                
                if success:
                    return JSONResponse({"success": True})
                else:
                    raise HTTPException(status_code=404, detail="Image not found")
                    
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")

        @router.post("/{image_id}/toggle")
        async def toggle_image(image_id: str):
            """Enable/disable image in slideshow"""
            try:
                success = self.metadata.toggle_image_enabled(image_id)
                
                if success:
                    image = self.metadata.get_image_by_id(image_id)
                    return JSONResponse({
                        "success": True, 
                        "enabled": image["enabled"] if image else False
                    })
                else:
                    raise HTTPException(status_code=404, detail="Image not found")
                    
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Toggle failed: {str(e)}")

        @router.delete("/{image_id}")
        async def delete_image(image_id: str):
            """Delete image from collection and all galleries"""
            try:
                # Remove from all galleries first
                galleries = self.gallery_service.get_all_galleries()
                for gallery in galleries:
                    if image_id in gallery.content_ids:
                        gallery.content_ids.remove(image_id)
                        self.gallery_service.update_gallery(gallery.id, gallery)
                
                # Delete the image files and metadata
                success = self.metadata.delete_image(image_id)
                
                if success:
                    return JSONResponse({"success": True})
                else:
                    raise HTTPException(status_code=404, detail="Image not found")
                    
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

        @router.post("/reorder")
        async def reorder_images(request: Request):
            """Reorder images by updating sort_order within a specific gallery"""
            try:
                data = await request.json()
                dragged_id = data.get("dragged_id")
                target_id = data.get("target_id")
                gallery_id = data.get("gallery_id")

                if not dragged_id or not target_id or not gallery_id:
                    raise HTTPException(status_code=400, detail="dragged_id, target_id, and gallery_id are required")

                # Get all images for the specified gallery
                images = self.metadata.get_images_by_gallery(gallery_id)
                if not images:
                    raise HTTPException(status_code=404, detail="Gallery not found or no images in gallery")

                images.sort(key=lambda x: x.get("sort_order", 0))

                # Find the dragged and target images
                dragged_img = next((img for img in images if img["id"] == dragged_id), None)
                target_img = next((img for img in images if img["id"] == target_id), None)

                if not dragged_img or not target_img:
                    raise HTTPException(status_code=404, detail="Image not found")

                # Remove dragged image from list
                images = [img for img in images if img["id"] != dragged_id]

                # Find target position and insert dragged image
                target_index = next((i for i, img in enumerate(images) if img["id"] == target_id), None)
                if target_index is not None:
                    images.insert(target_index, dragged_img)

                # Update sort_order for all images
                for i, img in enumerate(images):
                    self.metadata.update_image(img["id"], {"sort_order": i})

                return {"message": "Images reordered successfully"}

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Reorder failed: {str(e)}")
        
        return router


# Factory function for creating router with dependencies
def create_images_router(image_service: ImageService, gallery_service: GalleryService, 
                        storage_service: StorageService, metadata_manager, image_processor) -> APIRouter:
    """Factory function to create images router with injected dependencies"""
    routes = ImageRoutes(image_service, gallery_service, storage_service, metadata_manager, image_processor)
    return routes.create_router()


# Default router for backward compatibility (will be created in main channel)
router = APIRouter(prefix="/images", tags=["images"])
