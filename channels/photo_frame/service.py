"""
Standalone Photo Frame Channel Service
Runs the photo frame channel as an independent FastAPI service for the plugin architecture
"""
import sys
import os
from pathlib import Path
import asyncio
from typing import Dict, Any, List

# Add the photo frame directory to Python path
photo_frame_dir = Path(__file__).parent
sys.path.insert(0, str(photo_frame_dir))

# Import the channel class
from channel import PhotoFrameChannel

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles


class PhotoFrameService:
    """Standalone service wrapper for PhotoFrameChannel"""
    
    def __init__(self):
        self.channel = PhotoFrameChannel(str(photo_frame_dir))
        self.app = self._create_app()
    
    def _create_app(self) -> FastAPI:
        """Create FastAPI application"""
        app = FastAPI(
            title="Photo Frame Channel Service",
            description="Standalone photo frame channel service",
            version="1.0.0"
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, specify actual origins
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Mount static assets
        assets_dir = photo_frame_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
        
        # Mount UI files
        ui_dir = photo_frame_dir / "ui"
        if ui_dir.exists():
            app.mount("/ui", StaticFiles(directory=str(ui_dir)), name="ui")
        
        self._setup_routes(app)
        return app
    
    def _setup_routes(self, app: FastAPI):
        """Setup all API routes"""
        
        @app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "service": "photo-frame-channel",
                "version": "1.0.0"
            }
        
        @app.get("/manifest")
        async def get_manifest():
            """Get dynamic manifest with current galleries"""
            try:
                # Get current galleries from the channel
                galleries_result = self.channel.list_subchannels()
                galleries = galleries_result.get("subchannels", [])
                
                # Build image endpoints from galleries
                image_endpoints = []
                for gallery in galleries:
                    # Get gallery settings for current values
                    gallery_settings = self.channel.get_subchannel_settings(gallery["id"])
                    
                    image_endpoints.append({
                        "id": gallery["id"],
                        "name": gallery["name"],
                        "description": gallery.get("description", ""),
                        "source": f"/galleries/{gallery['id']}",
                        "options": [
                            {
                                "name": "order_mode",
                                "type": "string",
                                "value": gallery_settings.get("order_mode", {}).get("value", "added"),
                                "options_source": f"/galleries/{gallery['id']}/options/order_mode"
                            },
                            {
                                "name": "crop_mode", 
                                "type": "string",
                                "value": gallery_settings.get("crop_mode", {}).get("value", "smart_crop"),
                                "options_source": f"/galleries/{gallery['id']}/options/crop_mode"
                            },
                            {
                                "name": "update_interval_unit",
                                "type": "string", 
                                "value": gallery_settings.get("update_interval_unit", {}).get("value", "minutes"),
                                "options_source": f"/galleries/{gallery['id']}/options/update_interval_unit"
                            },
                            {
                                "name": "update_interval_value",
                                "type": "integer",
                                "value": gallery_settings.get("update_interval_value", {}).get("value", 30)
                            },
                            {
                                "name": "width",
                                "type": "integer",
                                "value": 800
                            },
                            {
                                "name": "height", 
                                "type": "integer",
                                "value": 480
                            }
                        ]
                    })
                
                return {
                    "id": "com.epaperframe.photoframe",
                    "name": "Photo Frame",
                    "description": "Gallery-based photo slideshow",
                    "icon": "/assets/icon.png",
                    "imageEndpoints": image_endpoints,
                    "uiComponent": "/ui/manage.esm.js",
                    "staticAssets": "/assets"
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to generate manifest: {str(e)}")
        
        @app.post("/request_image")
        async def request_image(request_data: Dict[str, Any]):
            """Request image generation"""
            try:
                endpoint_id = request_data.get("endpoint_id")
                options = request_data.get("options", {})
                
                if not endpoint_id:
                    raise HTTPException(status_code=400, detail="endpoint_id required")
                
                # Get current image from the specified gallery
                current_result = self.channel.get_current_content(endpoint_id)
                if not current_result:
                    raise HTTPException(status_code=404, detail="No images available in gallery")
                
                file_path, file_info = current_result
                
                # Read the file and return as bytes
                with open(file_path, 'rb') as f:
                    image_data = f.read()
                
                return Response(content=image_data, media_type="image/jpeg")
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to generate image: {str(e)}")
        
        # Proxy all other requests to the channel's existing router
        channel_router = self.channel.get_router()
        if channel_router:
            app.include_router(channel_router, prefix="")


def create_service() -> FastAPI:
    """Create and return the service application"""
    service = PhotoFrameService()
    return service.app


# For running standalone
if __name__ == "__main__":
    import uvicorn
    
    app = create_service()
    uvicorn.run(app, host="127.0.0.1", port=8001, reload=True)
