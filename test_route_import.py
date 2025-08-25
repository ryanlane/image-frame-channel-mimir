#!/usr/bin/env python3
"""
Test route creation and import
"""

import sys
import os
from pathlib import Path

# Add the channel directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'channels', 'photo_frame'))

def test_route_import():
    """Test if the routes can be imported and created"""
    print("Testing Route Import and Creation")
    print("=" * 40)
    
    try:
        from services.gallery_service import GalleryService
        from models.settings import SettingsManager
        from routes.settings import SubchannelSettingsRoutes
        
        print("✅ All imports successful")
        
        # Create dummy services
        temp_path = Path("/tmp")
        gallery_service = GalleryService(temp_path)
        settings_manager = SettingsManager()
        
        print("✅ Services created")
        
        # Create the route handler
        route_handler = SubchannelSettingsRoutes(gallery_service, settings_manager)
        router = route_handler.create_router()
        
        print("✅ Router created")
        print(f"   Router prefix: {router.prefix}")
        print(f"   Router tags: {router.tags}")
        
        # Check routes
        route_count = len(router.routes)
        print(f"   Total routes: {route_count}")
        
        for route in router.routes:
            print(f"   - {route.methods} {route.path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_route_import()
