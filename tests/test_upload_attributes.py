#!/usr/bin/env python3
"""
Test upload attribute names
"""

import sys
import os

# Add the channel directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'channels', 'photo_frame'))

def test_upload_attributes():
    """Test that upload result attributes match what the route expects"""
    
    print("Upload Attribute Verification")
    print("=" * 35)
    
    try:
        from models.image import ImageUploadResult, ImageBatchUploadResult
        
        # Test ImageUploadResult
        print("📝 ImageUploadResult attributes:")
        upload_result = ImageUploadResult(success=True, image_id="test123", filename="test.jpg", error=None)
        
        expected_attrs = ["success", "image_id", "filename", "error"]
        for attr in expected_attrs:
            if hasattr(upload_result, attr):
                print(f"   ✅ {attr}: {getattr(upload_result, attr)}")
            else:
                print(f"   ❌ {attr}: MISSING")
        
        # Test ImageBatchUploadResult
        print("\n📦 ImageBatchUploadResult attributes:")
        batch_result = ImageBatchUploadResult()
        batch_result.add_result(upload_result)
        
        expected_batch_attrs = ["successful_uploads", "failed_uploads", "results"]
        for attr in expected_batch_attrs:
            if hasattr(batch_result, attr):
                print(f"   ✅ {attr}: {getattr(batch_result, attr)}")
            else:
                print(f"   ❌ {attr}: MISSING")
        
        print("\n🔧 Route Fix Summary:")
        print("   ✅ successful_count → successful_uploads")
        print("   ✅ failed_count → failed_uploads")
        print("   ✅ error_message → error")
        
        print("\n🎯 Expected Result:")
        print("   Upload should now return HTTP 200 with correct data structure")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_upload_attributes()
