#!/usr/bin/env python3
"""
Test the complete frontend save flow - both API calls
"""

import json
import tempfile
from pathlib import Path
import sys
import os

# Add the channel directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'channels', 'photo_frame'))

def test_frontend_save_flow():
    """Test the complete frontend save flow with both API calls"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        data_dir = temp_path / "data"
        data_dir.mkdir(exist_ok=True)
        
        # Create test galleries file
        galleries_file = data_dir / "galleries.json"
        test_galleries = [
            {
                "id": "test_save",
                "name": "Original Name",
                "description": "Original description",
                "contentIds": ["img1", "img2"],
                "tags": [],
                "created": "2024-01-01T00:00:00Z",
                "modified": "2024-01-01T00:00:00Z",
                "imageCount": 2,
                "coverImageId": "img1",
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
        
        from services.gallery_service import GalleryService
        from models.gallery import GalleryUpdate
        from models.settings import SettingsManager
        
        gallery_service = GalleryService(temp_path)
        settings_manager = SettingsManager()
        
        print("Frontend Save Flow Test")
        print("=" * 50)
        
        # Simulate the frontend's two API calls
        print("\n🔄 Simulating Frontend Save Process...")
        
        # CALL 1: Update gallery metadata (name, description)
        print("\n1️⃣ Updating gallery metadata...")
        gallery_metadata = {
            "name": "Updated Gallery Name",
            "description": "Updated gallery description"
        }
        
        try:
            update_data = GalleryUpdate(
                name=gallery_metadata["name"],
                description=gallery_metadata["description"]
            )
            gallery_result = gallery_service.update_gallery("test_save", update_data)
            print(f"   ✅ Gallery metadata updated: {gallery_result.name}")
            metadata_success = True
        except Exception as e:
            print(f"   ❌ Gallery metadata update failed: {e}")
            metadata_success = False
        
        # CALL 2: Update gallery settings
        print("\n2️⃣ Updating gallery settings...")
        gallery_settings = {
            "order_mode": "random",
            "crop_mode": "fit",
            "update_interval_value": 45,
            "update_interval_unit": "seconds"
        }
        
        try:
            settings_result = gallery_service.update_gallery_settings("test_save", gallery_settings)
            print(f"   ✅ Gallery settings updated: {settings_result}")
            settings_success = True
        except Exception as e:
            print(f"   ❌ Gallery settings update failed: {e}")
            settings_success = False
        
        # FRONTEND LOGIC: Check if both succeeded
        print(f"\n📊 Results Summary:")
        print(f"   Metadata update: {'✅ SUCCESS' if metadata_success else '❌ FAILED'}")
        print(f"   Settings update: {'✅ SUCCESS' if settings_success else '❌ FAILED'}")
        
        if metadata_success and settings_success:
            print("\n🎉 FRONTEND SHOULD SHOW: Settings saved successfully!")
            print("   ✅ No error modal should appear")
            
            # Verify the changes persisted
            final_gallery = gallery_service.get_gallery("test_save")
            final_settings = gallery_service.get_gallery_settings("test_save")
            
            print(f"\n🔍 Verification:")
            print(f"   Final name: {final_gallery.name}")
            print(f"   Final description: {final_gallery.description}")
            print(f"   Final crop_mode: {final_settings.get('crop_mode')}")
            print(f"   Final order_mode: {final_settings.get('order_mode')}")
            
            return True
        else:
            print("\n❌ FRONTEND WOULD SHOW: Error saving settings")
            print("   This is the issue you were experiencing!")
            return False

if __name__ == "__main__":
    test_frontend_save_flow()
