#!/usr/bin/env python3
"""
Simple test to debug the GallerySettings validation issue
"""

import sys
import os
from pathlib import Path

# Add the channel directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'channels', 'photo_frame'))

def test_gallery_settings_validation():
    """Test GallerySettings validation in isolation"""
    print("Testing GallerySettings validation in isolation")
    print("=" * 50)
    
    try:
        from models.settings import GallerySettings
        print("✅ Successfully imported GallerySettings")
    except Exception as e:
        print(f"❌ Failed to import GallerySettings: {e}")
        return False
    
    # Test 1: Valid settings
    print("\nTest 1: Valid settings")
    valid_settings = {
        "order_mode": "random",
        "crop_mode": "letterbox", 
        "update_interval_value": 60,
        "update_interval_unit": "seconds"
    }
    
    try:
        gallery_settings = GallerySettings(valid_settings)
        print(f"Created GallerySettings: {gallery_settings.to_dict()}")
        
        validation_errors = gallery_settings.validate()
        print(f"Validation errors: {validation_errors}")
        
        if validation_errors:
            print("❌ Test 1 failed - valid settings were rejected")
            print(f"Errors: {validation_errors}")
            return False
        else:
            print("✅ Test 1 passed - valid settings accepted")
            
    except Exception as e:
        print(f"❌ Test 1 failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Invalid settings
    print("\nTest 2: Invalid settings")
    invalid_settings = {
        "order_mode": "invalid_mode",
        "crop_mode": "smart_crop"
    }
    
    try:
        gallery_settings = GallerySettings(invalid_settings)
        validation_errors = gallery_settings.validate()
        print(f"Validation errors: {validation_errors}")
        
        if validation_errors:
            print("✅ Test 2 passed - invalid settings correctly rejected")
        else:
            print("❌ Test 2 failed - invalid settings were accepted")
            return False
            
    except Exception as e:
        print(f"❌ Test 2 failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n🎉 GallerySettings validation works correctly!")
    return True

if __name__ == "__main__":
    test_gallery_settings_validation()
