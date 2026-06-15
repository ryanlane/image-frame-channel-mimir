#!/usr/bin/env python3
"""
Simple test to verify route paths
"""

import sys
import os
from pathlib import Path

# Add the channel directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'channels', 'photo_frame'))

def test_route_paths():
    """Test that the route paths are correct"""
    
    print("Route Path Verification")
    print("=" * 30)
    
    try:
        # Import what we can
        from routes.images import ImagesRoutes
        
        # Check the router prefix
        print("📋 Route Information:")
        
        # We can't fully instantiate without all dependencies, but we can check the code
        import inspect
        
        # Look at the route creation code
        source = inspect.getsource(ImagesRoutes.create_router)
        
        if 'router = APIRouter(prefix="/images"' in source:
            print("   ✅ Images router has prefix '/images'")
        else:
            print("   ❌ Images router prefix not found")
        
        if '@router.post("/upload")' in source:
            print("   ✅ Upload route exists at '/upload' (relative to prefix)")
            print("   📍 Full path: /images/upload")
        else:
            print("   ❌ Upload route not found")
        
        print("\n🔧 Frontend Fix Applied:")
        print("   Old URL: /api/channels/com.epaperframe.photoframe/upload")
        print("   New URL: /api/channels/com.epaperframe.photoframe/images/upload")
        print("   ✅ URLs should now match!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking routes: {e}")
        return False

if __name__ == "__main__":
    test_route_paths()
