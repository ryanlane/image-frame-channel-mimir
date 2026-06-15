#!/usr/bin/env python3
"""
Test script to verify the FileMetadataManager is working correctly
"""

import sys
import json
from pathlib import Path

# Add the channel directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "channels" / "photo_frame"))

def test_metadata_system():
    """Test the file-based metadata system"""
    print("🧪 Testing FileMetadataManager...")
    
    try:
        from utils.file_metadata import FileMetadataManager
        
        # Create a test directory
        test_dir = Path(__file__).parent / "test_uploads"
        test_dir.mkdir(exist_ok=True)
        
        print(f"📁 Test directory: {test_dir}")
        
        # Initialize metadata manager
        metadata = FileMetadataManager(test_dir)
        print("✅ FileMetadataManager initialized")
        
        # Test adding an image
        test_image_data = {
            "filename": "test_image.jpg",
            "width": 640,
            "height": 480,
            "description": "Test image for metadata system"
        }
        
        print("📝 Adding test image metadata...")
        image_id = metadata.add_image(test_image_data)
        print(f"✅ Image added with ID: {image_id}")
        
        # Test retrieving all images
        print("📋 Retrieving all images...")
        all_images = metadata.get_all_images()
        print(f"✅ Found {len(all_images)} images")
        
        if all_images:
            print("📄 First image metadata:")
            print(json.dumps(all_images[0], indent=2))
        
        # Test retrieving by ID
        print(f"🔍 Retrieving image by ID: {image_id}")
        retrieved_image = metadata.get_image_by_id(image_id)
        if retrieved_image:
            print("✅ Image retrieved successfully")
            print(f"   Filename: {retrieved_image.get('filename')}")
            print(f"   Description: {retrieved_image.get('description')}")
        else:
            print("❌ Failed to retrieve image by ID")
            
        # Test updating image
        print("📝 Testing image update...")
        update_success = metadata.update_image(image_id, {
            "description": "Updated test image description",
            "tags": ["test", "metadata"]
        })
        
        if update_success:
            print("✅ Image updated successfully")
            updated_image = metadata.get_image_by_id(image_id)
            print(f"   New description: {updated_image.get('description')}")
            print(f"   Tags: {updated_image.get('tags')}")
        else:
            print("❌ Failed to update image")
            
        # Check files created
        print("📁 Checking created files...")
        meta_files = list(test_dir.glob("*.meta"))
        print(f"✅ Found {len(meta_files)} .meta files")
        for meta_file in meta_files:
            print(f"   📄 {meta_file.name}")
            
        # Cleanup
        print("🧹 Cleaning up test files...")
        for meta_file in meta_files:
            meta_file.unlink()
        test_dir.rmdir()
        print("✅ Cleanup complete")
        
        print("\n🎉 FileMetadataManager test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_metadata_system()
    sys.exit(0 if success else 1)
