"""
Settings management routes for Photo Frame Channel

Handles all settings-related endpoints including:
- Channel settings (global configuration)
- Gallery-specific settings (subchannel settings)
- Hardware configuration
- Settings validation and updates
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

# Import dependencies that will be injected
# Use absolute imports to avoid relative import issues
try:
    from services import GalleryService, StorageService
    from models import ChannelSettings, GallerySettings, SettingsManager
except ImportError:
    # Fallback for when running from channel directory
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from services import GalleryService, StorageService
    from models import ChannelSettings, GallerySettings, SettingsManager


class SettingsRoutes:
    """Settings routes class with dependency injection"""
    
    def __init__(self, gallery_service: GalleryService, storage_service: StorageService, 
                 settings_manager: SettingsManager, db, config):
        self.gallery_service = gallery_service
        self.storage_service = storage_service
        self.settings_manager = settings_manager
        self.db = db
        self._config = config
        
    def create_router(self) -> APIRouter:
        """Create and configure the settings router"""
        router = APIRouter(prefix="/settings", tags=["settings"])
        
        @router.get("")
        async def get_settings():
            """Get current photo frame configuration"""
            try:
                # Get settings from database or use defaults
                settings = self.db.get_settings()
                if not settings:
                    # Return defaults from config if no settings stored
                    settings = self._config.get("settings", {}).get("defaults", {})
                
                return JSONResponse({
                    "slideshow_enabled": {
                        "type": "boolean",
                        "value": settings.get("slideshow_enabled", True)
                    },
                    "order_mode": {
                        "type": "string", 
                        "value": settings.get("order_mode", "added")
                    },
                    "crop_mode": {
                        "type": "string",
                        "value": settings.get("crop_mode", "smart_crop")
                    },
                    "transition_effect": {
                        "type": "string",
                        "value": settings.get("transition_effect", "fade")
                    },
                    "update_interval_unit": {
                        "type": "string",
                        "value": settings.get("update_interval_unit", "minutes")
                    },
                    "update_interval_value": {
                        "type": "integer",
                        "value": settings.get("update_interval_value", 30)
                    }
                })
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get settings: {str(e)}")

        @router.put("")
        async def update_settings(request: Request):
            """Update photo frame configuration"""
            try:
                settings_data = await request.json()
                
                # Validate settings using the settings manager
                try:
                    validated_settings = self.settings_manager.validate_channel_settings(settings_data)
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
                
                # Save to database
                self.db.update_settings(validated_settings.dict())
                
                return JSONResponse({"success": True})
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Settings update failed: {str(e)}")

        @router.get("/hardware")
        async def get_hardware_info():
            """Get hardware configuration and status"""
            try:
                # This would typically query actual hardware
                # For now, return mock data based on config
                hardware_config = self._config.get("hardware", {})
                
                return JSONResponse({
                    "display_type": hardware_config.get("display_type", "unknown"),
                    "resolution": hardware_config.get("resolution", {"width": 800, "height": 600}),
                    "color_mode": hardware_config.get("color_mode", "color"),
                    "supported_formats": hardware_config.get("supported_formats", ["jpeg", "png"]),
                    "max_file_size": hardware_config.get("max_file_size", 10485760),  # 10MB
                    "status": "connected"
                })
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Hardware info failed: {str(e)}")
        
        return router


class SubchannelSettingsRoutes:
    """Subchannel (Gallery) settings routes with dependency injection"""
    
    def __init__(self, gallery_service: GalleryService, settings_manager: SettingsManager):
        self.gallery_service = gallery_service
        self.settings_manager = settings_manager
        
    def create_router(self) -> APIRouter:
        """Create and configure the subchannel settings router"""
        router = APIRouter(prefix="/subchannels", tags=["subchannels"])
        
        @router.get("/{subchannel_id}/settings")
        async def get_subchannel_settings(subchannel_id: str):
            """Get settings for a specific gallery (subchannel)"""
            try:
                # Note: gallery_service methods are synchronous, no await needed
                gallery_settings = self.gallery_service.get_gallery_settings(subchannel_id)
                
                return JSONResponse({
                    "slideshow_enabled": {
                        "type": "boolean",
                        "value": gallery_settings.get("slideshow_enabled", True)
                    },
                    "order_mode": {
                        "type": "string",
                        "value": gallery_settings.get("order_mode", "added")
                    },
                    "crop_mode": {
                        "type": "string", 
                        "value": gallery_settings.get("crop_mode", "smart_crop")
                    },
                    "transition_effect": {
                        "type": "string",
                        "value": gallery_settings.get("transition_effect", "fade")
                    },
                    "update_interval_value": {
                        "type": "integer",
                        "value": gallery_settings.get("update_interval_value", 30)
                    },
                    "update_interval_unit": {
                        "type": "string",
                        "value": gallery_settings.get("update_interval_unit", "minutes")
                    }
                })
                
            except ValueError as e:
                # Gallery not found
                raise HTTPException(status_code=404, detail=str(e))
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get gallery settings: {str(e)}")

        @router.put("/{subchannel_id}/settings")
        async def update_subchannel_settings(subchannel_id: str, request: Request):
            """Update settings for a specific gallery (subchannel)"""
            try:
                settings_data = await request.json()
                
                # Use the gallery service method to update settings
                # Note: this method is synchronous, no await needed
                success = self.gallery_service.update_gallery_settings(subchannel_id, settings_data)
                
                if success:
                    return JSONResponse({"success": True})
                else:
                    raise HTTPException(status_code=500, detail="Failed to update gallery settings")
                
            except ValueError as e:
                # Gallery not found or validation errors
                raise HTTPException(status_code=400, detail=str(e))
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Gallery settings update failed: {str(e)}")

        @router.post("/{subchannel_id}/images/reorder")
        async def reorder_gallery_images(subchannel_id: str, request: Request):
            """Reorder images within a specific gallery"""
            try:
                data = await request.json()
                dragged_id = data.get("dragged_id")
                target_id = data.get("target_id")
                
                if not dragged_id or not target_id:
                    raise HTTPException(status_code=400, detail="Both dragged_id and target_id required")
                
                # Reorder images in the gallery
                success = self.gallery_service.reorder_gallery_images(subchannel_id, dragged_id, target_id)
                
                if success:
                    return JSONResponse({"success": True})
                else:
                    raise HTTPException(status_code=500, detail="Failed to reorder images")
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Image reorder failed: {str(e)}")
        
        return router


# Factory functions for creating routers with dependencies
def create_settings_router(gallery_service: GalleryService, storage_service: StorageService, 
                          settings_manager: SettingsManager, db, config) -> APIRouter:
    """Factory function to create settings router with injected dependencies"""
    routes = SettingsRoutes(gallery_service, storage_service, settings_manager, db, config)
    return routes.create_router()


def create_subchannel_settings_router(gallery_service: GalleryService, 
                                     settings_manager: SettingsManager) -> APIRouter:
    """Factory function to create subchannel settings router with injected dependencies"""
    routes = SubchannelSettingsRoutes(gallery_service, settings_manager)
    return routes.create_router()


# Default router for backward compatibility (will be created in main channel)
router = APIRouter(prefix="/settings", tags=["settings"])
