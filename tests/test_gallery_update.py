#!/usr/bin/env python3
"""
Test the new gallery metadata update endpoint
"""

import json
import tempfile
from pathlib import Path
import sys
import os

# Add the channel directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'channels', 'photo_frame'))

def test_gallery_metadata_update():
    """Test updating gallery name and description"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        data_dir = temp_path / "data"
        data_dir.mkdir(exist_ok=True)
        
        # Create test galleries file
        galleries_file = data_dir / "galleries.json"
        test_galleries = [
            {
                "id": "test_gallery",
                "name": "Old Name",
                "description": "Old description",
                "contentIds": ["img1"],
                "tags": [],
                "created": "2024-01-01T00:00:00Z",
                "modified": "2024-01-01T00:00:00Z",
                "imageCount": 1,
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
        
        gallery_service = GalleryService(temp_path)
        
        print("Testing Gallery Metadata Update")
        print("=" * 40)
        
        # Get initial state
        gallery = gallery_service.get_gallery("test_gallery")
        print(f"Initial name: {gallery.name}")
        print(f"Initial description: {gallery.description}")
        
        # Test updating metadata
        update_data = GalleryUpdate(
            name="New Gallery Name",
            description="Updated description"
        )
        
        try:
            updated_gallery = gallery_service.update_gallery("test_gallery", update_data)
            print(f"Updated name: {updated_gallery.name}")
            print(f"Updated description: {updated_gallery.description}")
            
            # Verify the update persisted
            gallery_check = gallery_service.get_gallery("test_gallery")
            if (gallery_check.name == "New Gallery Name" and 
                gallery_check.description == "Updated description"):
                print("✅ Gallery metadata update works correctly!")
                return True
            else:
                print("❌ Update didn't persist correctly")
                return False
                
        except Exception as e:
            print(f"❌ Update failed: {e}")
            return False

if __name__ == "__main__":
    test_gallery_metadata_update()
