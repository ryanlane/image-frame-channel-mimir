"""
Route modules for Photo Frame Channel

This package contains organized route modules that extract routing logic
from the main channel.py file for better maintainability.
"""

from .images import create_images_router
from .galleries import create_galleries_router
from .settings import create_settings_router, create_subchannel_settings_router
from .assets import create_assets_router, create_legacy_assets_router
from .admin import create_admin_router

# Default routers for backward compatibility
from .images import router as images_router
from .galleries import router as galleries_router
from .settings import router as settings_router
from .assets import router as assets_router
from .admin import router as admin_router

__all__ = [
    # Factory functions
    "create_images_router",
    "create_galleries_router", 
    "create_settings_router",
    "create_subchannel_settings_router",
    "create_assets_router",
    "create_legacy_assets_router",
    "create_admin_router",
    # Default routers
    "images_router",
    "galleries_router",
    "settings_router", 
    "assets_router",
    "admin_router"
]
