#!/usr/bin/env python3
"""
Full system test for gallery image reordering functionality
Tests the complete chain: UI -> Route -> Service -> Model -> File
"""

import json
import tempfile
from pathlib import Path
import sys
import os

# Add the channel directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'channels', 'photo_frame'))

def test_full_reorder_system():
    """Test the complete reordering system"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        data_dir = temp_path / "data"
        data_dir.mkdir(exist_ok=True)
        
        # Create test galleries file
        galleries_file = data_dir / "galleries.json"
        test_galleries = [
            {
                "id": "test-gallery",
                "name": "Test Gallery",
                "description": "Test gallery for reordering",
                "contentIds": ["1", "2", "3", "4", "5"],
                "tags": [],
                "created": "2024-01-01T00:00:00Z",
                "modified": "2024-01-01T00:00:00Z",
                "imageCount": 5,
                "coverImageId": "1",
                "displaySettings": {}
            }
        ]
        
        with open(galleries_file, 'w', encoding='utf-8') as f:
            json.dump(test_galleries, f, indent=2)
        
        # Import the real components
        from services.gallery_service import GalleryService
        from models.gallery import Gallery
        
        print("Testing Full Gallery Reordering System")
        print("=" * 50)
        
        # Initialize the service with real components
        gallery_service = GalleryService(temp_path)
        
        # Test initial state
        galleries = gallery_service.get_all_galleries()
        print(f"Loaded {len(galleries)} galleries")
        
        test_gallery = gallery_service.get_gallery("test-gallery")
        if not test_gallery:
            print("❌ Test gallery not found!")
            return False
        
        print(f"Initial order: {test_gallery.content_ids}")
        
        # Test 1: Move image '3' to before image '1'
        print("\nTest 1: Move '3' to before '1'")
        print(f"Before: {test_gallery.content_ids}")
        
        success = gallery_service.reorder_gallery_images("test-gallery", "3", "1")
        print(f"Reorder success: {success}")
        
        # Reload to verify persistence
        test_gallery = gallery_service.get_gallery("test-gallery")
        print(f"After: {test_gallery.content_ids}")
        expected = ["3", "1", "2", "4", "5"]
        
        if test_gallery.content_ids == expected:
            print("✅ Test 1 passed")
        else:
            print(f"❌ Test 1 failed - expected {expected}, got {test_gallery.content_ids}")
            return False
        
        # Test 2: Move image '1' to before image '5'
        print("\nTest 2: Move '1' to before '5'")
        print(f"Before: {test_gallery.content_ids}")
        
        success = gallery_service.reorder_gallery_images("test-gallery", "1", "5")
        print(f"Reorder success: {success}")
        
        # Reload to verify persistence
        test_gallery = gallery_service.get_gallery("test-gallery")
        print(f"After: {test_gallery.content_ids}")
        expected = ["3", "2", "4", "1", "5"]
        
        if test_gallery.content_ids == expected:
            print("✅ Test 2 passed")
        else:
            print(f"❌ Test 2 failed - expected {expected}, got {test_gallery.content_ids}")
            return False
        
        # Test 3: Move image '5' to before image '3' (to beginning)
        print("\nTest 3: Move '5' to before '3' (to beginning)")
        print(f"Before: {test_gallery.content_ids}")
        
        success = gallery_service.reorder_gallery_images("test-gallery", "5", "3")
        print(f"Reorder success: {success}")
        
        # Reload to verify persistence
        test_gallery = gallery_service.get_gallery("test-gallery")
        print(f"After: {test_gallery.content_ids}")
        expected = ["5", "3", "2", "4", "1"]
        
        if test_gallery.content_ids == expected:
            print("✅ Test 3 passed")
        else:
            print(f"❌ Test 3 failed - expected {expected}, got {test_gallery.content_ids}")
            return False
        
        # Test 4: Verify file persistence 
        print("\nTest 4: File persistence verification")
        
        # Create a new service instance to test file loading
        gallery_service2 = GalleryService(temp_path)
        test_gallery2 = gallery_service2.get_gallery("test-gallery")
        
        print(f"Loaded from file: {test_gallery2.content_ids}")
        
        if test_gallery2.content_ids == expected:
            print("✅ Test 4 passed - file persistence works")
        else:
            print(f"❌ Test 4 failed - file persistence broken")
            return False
        
        # Test error handling
        print("\nTest 5: Error handling")
        try:
            gallery_service.reorder_gallery_images("nonexistent", "1", "2")
            print("❌ Should have raised error for nonexistent gallery")
            return False
        except ValueError as e:
            print(f"✅ Correctly caught error: {e}")
        
        try:
            gallery_service.reorder_gallery_images("test-gallery", "999", "1")
            print("❌ Should have raised error for nonexistent image")
            return False
        except:
            print("✅ Correctly caught error for nonexistent image")
        
        print("\n🎉 All tests passed! Full system works correctly.")
        
        # Show final state
        print(f"\nFinal gallery state:")
        final_gallery = gallery_service.get_gallery("test-gallery")
        print(f"  ID: {final_gallery.id}")
        print(f"  Name: {final_gallery.name}")
        print(f"  Content IDs: {final_gallery.content_ids}")
        print(f"  Image Count: {final_gallery.image_count}")
        print(f"  Modified: {final_gallery.modified}")
        
        return True

if __name__ == "__main__":
    if test_full_reorder_system():
        print("\n✅ All systems functional!")
        sys.exit(0)
    else:
        print("\n❌ System has issues!")
        sys.exit(1)
