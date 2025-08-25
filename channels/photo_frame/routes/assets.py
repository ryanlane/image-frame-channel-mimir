"""
Asset serving routes for Photo Frame Channel

Handles all static file serving including:
- Uploaded images (full resolution)
- Thumbnail images (optimized for web)
- Legacy thumbnail endpoints
- Proper caching and media type handling
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

# Import dependencies that will be injected
# Use absolute imports to avoid relative import issues
try:
    from services import StorageService
except ImportError:
    # Fallback for when running from channel directory
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from services import StorageService


class AssetRoutes:
    """Asset routes class with dependency injection"""
    
    def __init__(self, storage_service: StorageService, channel_dir: Path):
        self.storage_service = storage_service
        self.channel_dir = channel_dir
        
    def create_router(self) -> APIRouter:
        """Create and configure the assets router"""
        router = APIRouter(prefix="/assets", tags=["assets"])
        
        @router.get("/uploads/{filename}")
        async def get_upload_file(filename: str):
            """Serve uploaded files (images and thumbnails)"""
            try:
                file_path = self.channel_dir / "assets" / "uploads" / filename
                
                if not file_path.exists():
                    raise HTTPException(status_code=404, detail="File not found")
                
                # Determine media type
                if filename.endswith(('.jpg', '.jpeg')):
                    media_type = "image/jpeg"
                elif filename.endswith('.png'):
                    media_type = "image/png"
                elif filename.endswith('.gif'):
                    media_type = "image/gif"
                elif filename.endswith('.webp'):
                    media_type = "image/webp"
                else:
                    media_type = "application/octet-stream"
                
                # Set cache headers for images
                cache_headers = {"Cache-Control": "max-age=3600"}  # 1 hour cache
                
                return FileResponse(
                    path=str(file_path),
                    media_type=media_type,
                    headers=cache_headers
                )
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"File serving failed: {str(e)}")

        return router


class LegacyAssetRoutes:
    """Legacy asset routes for backward compatibility"""
    
    def __init__(self, storage_service: StorageService, channel_dir: Path):
        self.storage_service = storage_service
        self.channel_dir = channel_dir
        
    def create_router(self) -> APIRouter:
        """Create and configure the legacy assets router"""
        router = APIRouter(prefix="/data", tags=["legacy-assets"])
        
        @router.get("/thumbs/{filename}")
        async def get_thumbnail(filename: str):
            """Serve thumbnail images (legacy endpoint)"""
            try:
                # Convert to new thumbnail format
                base_name = Path(filename).stem
                thumb_filename = f"{base_name}.thumb.jpg"
                thumb_path = self.channel_dir / "assets" / "uploads" / thumb_filename
                
                if not thumb_path.exists():
                    # Try to generate thumbnail if original exists
                    original_path = self.channel_dir / "assets" / "uploads" / filename
                    if original_path.exists():
                        # Use storage service to generate missing thumbnail
                        await self.storage_service.ensure_thumbnail_exists(str(original_path))
                        
                        # Check again
                        if not thumb_path.exists():
                            raise HTTPException(status_code=404, detail="Thumbnail generation failed")
                    else:
                        raise HTTPException(status_code=404, detail="Thumbnail not found")
                
                return FileResponse(
                    path=str(thumb_path),
                    media_type="image/jpeg",
                    headers={"Cache-Control": "max-age=3600"}
                )
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Thumbnail serving failed: {str(e)}")

        return router


# Factory functions for creating routers with dependencies
def create_assets_router(storage_service: StorageService, channel_dir: Path) -> APIRouter:
    """Factory function to create assets router with injected dependencies"""
    routes = AssetRoutes(storage_service, channel_dir)
    return routes.create_router()


def create_legacy_assets_router(storage_service: StorageService, channel_dir: Path) -> APIRouter:
    """Factory function to create legacy assets router with injected dependencies"""
    routes = LegacyAssetRoutes(storage_service, channel_dir)
    return routes.create_router()


# Default router for backward compatibility (will be created in main channel)
router = APIRouter(prefix="/assets", tags=["assets"])
