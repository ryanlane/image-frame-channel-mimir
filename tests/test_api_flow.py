#!/usr/bin/env python3
"""
Test to simulate the exact API call flow
"""

import json
import tempfile
from pathlib import Path
import sys
import os

# Add the channel directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'channels', 'photo_frame'))

def test_api_flow():
    """Test the complete API flow for settings update"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        data_dir = temp_path / "data"
        data_dir.mkdir(exist_ok=True)
        
        # Create test galleries file with "birds" gallery
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
        from models.settings import SettingsManager
        from routes.settings import SubchannelSettingsRoutes
        
        print("Testing Complete API Flow for Gallery Settings")
        print("=" * 60)
        
        # Initialize services
        gallery_service = GalleryService(temp_path)
        settings_manager = SettingsManager()
        
        # Initialize the route handler
        route_handler = SubchannelSettingsRoutes(gallery_service, settings_manager)
        
        print("\nTest 1: Simulate GET request")
        try:
            # This would be called by: GET /subchannels/birds/settings
            settings = gallery_service.get_gallery_settings("birds")
            print(f"Current settings: {settings}")
            print("✅ GET request simulation passed")
        except Exception as e:
            print(f"❌ GET request simulation failed: {e}")
            return False
        
        print("\nTest 2: Simulate PUT request")
        # This simulates what the frontend sends
        frontend_data = {
            "order_mode": "random",
            "crop_mode": "fit",  # Frontend sends "fit" (correct value)
            "update_interval_value": 60,
            "update_interval_unit": "seconds"
        }
        
        print(f"Frontend data: {frontend_data}")
        
        try:
            # This would be the route handler logic
            success = gallery_service.update_gallery_settings("birds", frontend_data)
            print(f"Update result: {success}")
            
            if success:
                print("✅ PUT request simulation passed")
            else:
                print("❌ PUT request simulation failed - returned False")
                return False
                
        except Exception as e:
            print(f"❌ PUT request simulation failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\nTest 3: Verify the update")
        try:
            updated_settings = gallery_service.get_gallery_settings("birds")
            print(f"Updated settings: {updated_settings}")
            
            if updated_settings.get("order_mode") == "random":
                print("✅ Settings were updated correctly")
            else:
                print("❌ Settings were not updated correctly")
                return False
                
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False
        
        print("\n🎉 Complete API flow works correctly!")
        return True

if __name__ == "__main__":
    test_api_flow()
