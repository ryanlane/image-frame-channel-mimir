#!/usr/bin/env python3
"""
Test all frontend crop mode values
"""

import json
import tempfile
from pathlib import Path
import sys
import os

# Add the channel directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'channels', 'photo_frame'))

def test_all_crop_modes():
    """Test all crop mode values that frontend can send"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        data_dir = temp_path / "data"
        data_dir.mkdir(exist_ok=True)
        
        # Create test galleries file with "test" gallery
        galleries_file = data_dir / "galleries.json"
        test_galleries = [
            {
                "id": "test",
                "name": "Test Gallery",
                "description": "Test",
                "contentIds": ["1"],
                "tags": [],
                "created": "2024-01-01T00:00:00Z",
                "modified": "2024-01-01T00:00:00Z",
                "imageCount": 1,
                "coverImageId": "1",
                "displaySettings": {
                    "order_mode": "added",
                    "crop_mode": "smart_crop",
                    "update_interval_value": 30,
                    "update_interval_unit": "minutes"
                }
            }
        ]
        
        with open(galleries_file, 'w', encoding='utf-8') as f:
            json.dump(test_galleries, f, indent=2)
        
        # Import components
        from services.gallery_service import GalleryService
        
        gallery_service = GalleryService(temp_path)
        
        print("Testing All Frontend Crop Mode Values")
        print("=" * 50)
        
        # Test all crop modes that frontend offers
        crop_modes = ["smart_crop", "fit", "fill"]
        
        for crop_mode in crop_modes:
            print(f"\nTesting crop_mode: {crop_mode}")
            
            test_data = {
                "order_mode": "added",
                "crop_mode": crop_mode,
                "update_interval_value": 30,
                "update_interval_unit": "minutes"
            }
            
            try:
                success = gallery_service.update_gallery_settings("test", test_data)
                if success:
                    print(f"✅ {crop_mode} - PASSED")
                else:
                    print(f"❌ {crop_mode} - FAILED (returned False)")
            except Exception as e:
                print(f"❌ {crop_mode} - FAILED ({e})")
        
        print("\n🎉 All crop modes tested!")

if __name__ == "__main__":
    test_all_crop_modes()
