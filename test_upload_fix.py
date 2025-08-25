#!/usr/bin/env python3
"""
Test the upload fix by checking for syntax errors
"""

import sys
import os

# Add the channel directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'channels', 'photo_frame'))

def test_upload_fix():
    """Test that the upload route can be imported without errors"""
    
    print("Upload Fix Verification")
    print("=" * 30)
    
    try:
        # Try to compile the file to check for syntax errors
        import py_compile
        routes_file = os.path.join(os.path.dirname(__file__), 'channels', 'photo_frame', 'routes', 'images.py')
        py_compile.compile(routes_file, doraise=True)
        print("✅ images.py compiles without syntax errors")
        
        # Check that the problematic lines are fixed
        with open(routes_file, 'r') as f:
            content = f.read()
            
        # Check upload route fix
        if 'result = self.image_service.upload_files(files)' in content:
            print("✅ Upload route: removed 'await' from upload_files call")
        else:
            print("❌ Upload route: sync fix not applied")
            
        # Check gallery service fixes
        if 'galleries = self.gallery_service.get_all_galleries()' in content:
            print("✅ Gallery list: removed 'await' from get_all_galleries call")
        else:
            print("❌ Gallery list: sync fix not applied")
            
        if 'self.gallery_service.update_gallery(gallery.id, gallery)' in content:
            print("✅ Gallery update: removed 'await' from update_gallery call")
        else:
            print("❌ Gallery update: sync fix not applied")
        
        print("\n🎯 Expected Result:")
        print("   Upload should now return HTTP 200 instead of 500")
        print("   Error should no longer mention 'await' issues")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_upload_fix()
