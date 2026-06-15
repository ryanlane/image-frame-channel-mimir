#!/usr/bin/env python3
"""
Test script for gallery settings functionality
"""

import json
import tempfile
from pathlib import Path
import sys
import os

# Add the channel directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'channels', 'photo_frame'))

def test_gallery_settings():
    """Test the gallery settings functionality"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        data_dir = temp_path / "data"
        data_dir.mkdir(exist_ok=True)
        
        # Create test galleries file
        galleries_file = data_dir / "galleries.json"
        test_galleries = [
            {
                "id": "birds",
                "name": "Birds Gallery",
                "description": "Bird photos",
                "contentIds": ["1", "2", "3"],
                "tags": [],
                "created": "2024-01-01T00:00:00Z",
                "modified": "2024-01-01T00:00:00Z",
                "imageCount": 3,
                "coverImageId": "1",
                "displaySettings": {
                    "order_mode": "added",
                    "crop_mode": "smart_crop"
                }
            }
        ]
        
        with open(galleries_file, 'w', encoding='utf-8') as f:
            json.dump(test_galleries, f, indent=2)
        
        # Import the real components
        from services.gallery_service import GalleryService
        
        print("Testing Gallery Settings Functionality")
        print("=" * 50)
        
        # Initialize the service
        gallery_service = GalleryService(temp_path)
        
        # Test 1: Get existing settings
        print("\nTest 1: Get existing settings")
        settings = gallery_service.get_gallery_settings("birds")
        print(f"Current settings: {settings}")
        
        expected_order = settings.get("order_mode")
        expected_crop = settings.get("crop_mode")
        print(f"Order mode: {expected_order}")
        print(f"Crop mode: {expected_crop}")
        
        if expected_order == "added" and expected_crop == "smart_crop":
            print("✅ Test 1 passed - settings loaded correctly")
        else:
            print(f"❌ Test 1 failed - unexpected settings")
            return False
        
        # Test 2: Update settings
        print("\nTest 2: Update settings")
        new_settings = {
            "order_mode": "random",
            "crop_mode": "letterbox",
            "update_interval_value": 60,
            "update_interval_unit": "seconds"
        }
        
        try:
            success = gallery_service.update_gallery_settings("birds", new_settings)
            print(f"Update success: {success}")
            
            if success:
                print("✅ Test 2 passed - settings updated successfully")
            else:
                print("❌ Test 2 failed - update returned False")
                return False
                
        except Exception as e:
            print(f"❌ Test 2 failed - exception: {e}")
            return False
        
        # Test 3: Verify settings were saved
        print("\nTest 3: Verify settings persistence")
        
        # Create new service instance to test loading from file
        gallery_service2 = GalleryService(temp_path)
        updated_settings = gallery_service2.get_gallery_settings("birds")
        
        print(f"Loaded settings: {updated_settings}")
        
        if (updated_settings.get("order_mode") == "random" and 
            updated_settings.get("crop_mode") == "letterbox" and
            updated_settings.get("update_interval_value") == 60 and
            updated_settings.get("update_interval_unit") == "seconds"):
            print("✅ Test 3 passed - settings persisted correctly")
        else:
            print("❌ Test 3 failed - settings not persisted correctly")
            return False
        
        # Test 4: Test validation
        print("\nTest 4: Test validation")
        invalid_settings = {
            "order_mode": "invalid_mode",
            "crop_mode": "smart_crop"
        }
        
        try:
            gallery_service.update_gallery_settings("birds", invalid_settings)
            print("❌ Test 4 failed - should have rejected invalid settings")
            return False
        except ValueError as e:
            print(f"✅ Test 4 passed - correctly rejected invalid settings: {e}")
        except Exception as e:
            print(f"❌ Test 4 failed - unexpected exception: {e}")
            return False
        
        # Test 5: Test nonexistent gallery
        print("\nTest 5: Test nonexistent gallery")
        try:
            gallery_service.get_gallery_settings("nonexistent")
            print("❌ Test 5 failed - should have thrown exception")
            return False
        except ValueError as e:
            print(f"✅ Test 5 passed - correctly handled nonexistent gallery: {e}")
        except Exception as e:
            print(f"❌ Test 5 failed - unexpected exception: {e}")
            return False
        
        print("\n🎉 All tests passed! Gallery settings functionality works correctly.")
        return True

if __name__ == "__main__":
    if test_gallery_settings():
        print("\n✅ Settings system functional!")
        sys.exit(0)
    else:
        print("\n❌ Settings system has issues!")
        sys.exit(1)
