#!/usr/bin/env python3
"""
Test script to validate the refactoring of image selection logic
"""

import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def test_image_service_import():
    """Test that ImageService can be imported and has get_next_image method"""
    try:
        from services.image_service import ImageService
        print("✅ ImageService imported successfully")
        
        # Check if get_next_image method exists
        if hasattr(ImageService, 'get_next_image'):
            print("✅ ImageService.get_next_image method exists")
        else:
            print("❌ ImageService.get_next_image method not found")
            return False
            
        return True
    except ImportError as e:
        print(f"❌ Failed to import ImageService: {e}")
        return False

def test_gallery_service_import():
    """Test that GalleryService can be imported and has updated get_next_image_from_gallery method"""
    try:
        from services.gallery_service import GalleryService
        print("✅ GalleryService imported successfully")
        
        # Check if get_next_image_from_gallery method exists
        if hasattr(GalleryService, 'get_next_image_from_gallery'):
            print("✅ GalleryService.get_next_image_from_gallery method exists")
            
            # Check method signature to see if it accepts image_service parameter
            import inspect
            sig = inspect.signature(GalleryService.get_next_image_from_gallery)
            params = list(sig.parameters.keys())
            
            if 'image_service' in params:
                print("✅ GalleryService.get_next_image_from_gallery accepts image_service parameter")
            else:
                print("❌ GalleryService.get_next_image_from_gallery missing image_service parameter")
                return False
        else:
            print("❌ GalleryService.get_next_image_from_gallery method not found")
            return False
            
        return True
    except ImportError as e:
        print(f"❌ Failed to import GalleryService: {e}")
        return False

def test_channel_import():
    """Test that PhotoFrameChannel can be imported and doesn't have the old methods"""
    try:
        from channel import PhotoFrameChannel
        print("✅ PhotoFrameChannel imported successfully")
        
        # Check that old methods are removed
        old_methods = ['_get_next_image', '_get_next_by_custom_order', '_get_next_by_date_added']
        
        for method_name in old_methods:
            if hasattr(PhotoFrameChannel, method_name):
                print(f"❌ Old method {method_name} still exists")
                return False
            else:
                print(f"✅ Old method {method_name} successfully removed")
                
        return True
    except ImportError as e:
        print(f"❌ Failed to import PhotoFrameChannel: {e}")
        return False

def test_image_service_functionality():
    """Test the ImageService.get_next_image method with mock data"""
    try:
        from services.image_service import ImageService
        from pathlib import Path
        
        # Create a mock ImageService (without actual files)
        class MockMetadata:
            def get_all_images(self):
                return [
                    {"id": "1", "filename": "test1.jpg", "enabled": True, "times_shown": 0, "created_at": "2023-01-01"},
                    {"id": "2", "filename": "test2.jpg", "enabled": True, "times_shown": 1, "created_at": "2023-01-02"},
                    {"id": "3", "filename": "test3.jpg", "enabled": False, "times_shown": 0, "created_at": "2023-01-03"}
                ]
            
            def get_enabled_images(self):
                return [img for img in self.get_all_images() if img.get("enabled", True)]
        
        mock_metadata = MockMetadata()
        image_service = ImageService(Path("."), mock_metadata)
        
        # Test different order modes
        test_settings = [
            {"order_mode": "random"},
            {"order_mode": "custom"},
            {"order_mode": "added"}
        ]
        
        for settings in test_settings:
            result = image_service.get_next_image(settings)
            if result:
                print(f"✅ get_next_image works for order_mode: {settings['order_mode']}")
            else:
                print(f"❌ get_next_image failed for order_mode: {settings['order_mode']}")
                return False
        
        return True
    except Exception as e:
        print(f"❌ ImageService functionality test failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("🧪 Testing Image Selection Logic Refactoring")
    print("=" * 50)
    
    tests = [
        test_image_service_import,
        test_gallery_service_import,
        test_channel_import,
        test_image_service_functionality
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        print(f"\n📋 Running: {test.__name__}")
        if test():
            passed += 1
            print("✅ PASSED")
        else:
            print("❌ FAILED")
    
    print("\n" + "=" * 50)
    print(f"🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Refactoring is successful.")
        return 0
    else:
        print("⚠️ Some tests failed. Please review the implementation.")
        return 1

if __name__ == "__main__":
    exit(main())
