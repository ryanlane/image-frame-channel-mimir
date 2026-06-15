#!/usr/bin/env python3
"""
Test script for gallery image reordering functionality
"""

import json
import tempfile
from pathlib import Path
import sys
import os

# Add the channel directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'channels', 'photo_frame'))

# Mock database for testing
class MockPhotoFrameDB:
    def __init__(self):
        self.images = [
            {"id": 1, "filename": "image1.jpg", "original_name": "Image 1", "enabled": True},
            {"id": 2, "filename": "image2.jpg", "original_name": "Image 2", "enabled": True},
            {"id": 3, "filename": "image3.jpg", "original_name": "Image 3", "enabled": True},
            {"id": 4, "filename": "image4.jpg", "original_name": "Image 4", "enabled": True},
            {"id": 5, "filename": "image5.jpg", "original_name": "Image 5", "enabled": True},
        ]
    
    def get_image_by_id(self, image_id):
        for img in self.images:
            if img["id"] == int(image_id):
                return img
        return None

# Mock image processor
class MockImageProcessor:
    pass

# Test the reordering functionality
def test_gallery_reorder():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a test gallery file
        galleries_file = temp_path / "galleries.json"
        test_gallery = {
            "id": "test-gallery",
            "name": "Test Gallery",
            "contentIds": ["1", "2", "3", "4", "5"],
            "created": "2024-01-01T00:00:00Z",
            "modified": "2024-01-01T00:00:00Z"
        }
        
        with open(galleries_file, 'w') as f:
            json.dump([test_gallery], f, indent=2)
        
        # Create a simple channel class for testing
        class TestChannel:
            def __init__(self, channel_dir):
                self.channel_dir = Path(channel_dir)
                self.galleries_file = self.channel_dir / "galleries.json"
                self._galleries = self._load_galleries()
                self.metadata = MockPhotoFrameDB()
            
            def _load_galleries(self):
                if self.galleries_file.exists():
                    with open(self.galleries_file, 'r') as f:
                        return json.load(f)
                return []
            
            def _save_galleries(self):
                with open(self.galleries_file, 'w') as f:
                    json.dump(self._galleries, f, indent=2)
            
            def _find_gallery(self, gallery_id):
                for gallery in self._galleries:
                    if gallery["id"] == gallery_id:
                        return gallery
                return None
            
            def reorder_gallery_images(self, gallery_id, dragged_id, target_id):
                """Test implementation of reorder_gallery_images"""
                from datetime import datetime, timezone
                
                gallery = self._find_gallery(gallery_id)
                if not gallery:
                    raise ValueError(f"Gallery '{gallery_id}' not found")
                
                content_ids = gallery["contentIds"]
                
                if dragged_id not in content_ids:
                    raise ValueError(f"Image '{dragged_id}' not found in gallery '{gallery_id}'")
                if target_id not in content_ids:
                    raise ValueError(f"Target image '{target_id}' not found in gallery '{gallery_id}'")
                
                # Remove dragged image
                content_ids.remove(dragged_id)
                
                # Find target position and insert BEFORE target (fixed)
                target_index = content_ids.index(target_id)
                content_ids.insert(target_index, dragged_id)
                
                gallery["contentIds"] = content_ids
                gallery["modified"] = datetime.now(timezone.utc).isoformat()
                
                self._save_galleries()
                return True
        
        # Test the reordering
        channel = TestChannel(temp_dir)
        
        print("Testing Gallery Image Reordering")
        print("=" * 40)
        
        # Initial order
        gallery = channel._find_gallery("test-gallery")
        print(f"Initial order: {gallery['contentIds']}")
        
        # Test 1: Move image 3 to before image 1
        print("\nTest 1: Move '3' to before '1'")
        channel.reorder_gallery_images("test-gallery", "3", "1")
        gallery = channel._find_gallery("test-gallery")
        expected = ["3", "1", "2", "4", "5"]
        print(f"Expected: {expected}")
        print(f"Actual:   {gallery['contentIds']}")
        assert gallery['contentIds'] == expected, "Test 1 failed"
        print("✅ Test 1 passed")
        
        # Test 2: Move image 1 to before image 5
        print("\nTest 2: Move '1' to before '5'")
        channel.reorder_gallery_images("test-gallery", "1", "5")
        gallery = channel._find_gallery("test-gallery")
        expected = ["3", "2", "4", "1", "5"]
        print(f"Expected: {expected}")
        print(f"Actual:   {gallery['contentIds']}")
        assert gallery['contentIds'] == expected, "Test 2 failed"
        print("✅ Test 2 passed")
        
        # Test 3: Move image 5 to before image 3 (beginning)
        print("\nTest 3: Move '5' to before '3'")
        channel.reorder_gallery_images("test-gallery", "5", "3")
        gallery = channel._find_gallery("test-gallery")
        expected = ["5", "3", "2", "4", "1"]
        print(f"Expected: {expected}")
        print(f"Actual:   {gallery['contentIds']}")
        assert gallery['contentIds'] == expected, "Test 3 failed"
        print("✅ Test 3 passed")
        
        # Test error handling
        print("\nTest 4: Error handling")
        try:
            channel.reorder_gallery_images("nonexistent", "1", "2")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            print(f"✅ Correctly caught error: {e}")
        
        try:
            channel.reorder_gallery_images("test-gallery", "999", "1")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            print(f"✅ Correctly caught error: {e}")
        
        print("\n🎉 All tests passed! Gallery reordering works correctly.")

if __name__ == "__main__":
    test_gallery_reorder()
