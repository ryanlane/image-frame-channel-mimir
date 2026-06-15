#!/usr/bin/env python3
"""
Test script for gallery-specific settings functionality
"""

import sys
import json
from pathlib import Path

# Add the channel directory to Python path
channel_dir = Path(__file__).resolve().parent.parent / "channels" / "photo_frame"
sys.path.insert(0, str(channel_dir))

from channel import PhotoFrameChannel

def test_gallery_settings():
    """Test gallery-specific settings functionality"""
    
    # Initialize channel
    channel = PhotoFrameChannel(str(channel_dir))
    
    print("🧪 Testing Gallery-Specific Settings")
    print("=" * 50)
    
    # Test 1: List galleries and their settings
    print("\n1. Current galleries and their settings:")
    galleries = channel.get_subchannels()
    for gallery in galleries:
        print(f"\n📁 Gallery: {gallery['name']} (ID: {gallery['id']})")
        try:
            settings = channel.get_gallery_settings(gallery['id'])
            print("   Settings:")
            for key, value in settings.items():
                print(f"     {key}: {value}")
        except Exception as e:
            print(f"   ❌ Error getting settings: {e}")
    
    # Test 2: Update settings for family_photos gallery
    print("\n\n2. Testing settings update for 'family_photos' gallery:")
    try:
        new_settings = {
            "order_mode": "random",
            "crop_mode": "letterbox", 
            "update_interval_value": 45,
            "update_interval_unit": "seconds"
        }
        
        print(f"   Updating with: {new_settings}")
        success = channel.update_gallery_settings("family_photos", new_settings)
        print(f"   ✅ Update successful: {success}")
        
        # Verify the update
        updated_settings = channel.get_gallery_settings("family_photos")
        print(f"   Updated settings: {updated_settings}")
        
    except Exception as e:
        print(f"   ❌ Error updating settings: {e}")
    
    # Test 3: Test invalid settings
    print("\n\n3. Testing invalid settings (should fail):")
    try:
        invalid_settings = {
            "order_mode": "invalid_mode",
            "update_interval_value": -5
        }
        
        print(f"   Trying invalid settings: {invalid_settings}")
        success = channel.update_gallery_settings("family_photos", invalid_settings)
        print(f"   ❌ This should have failed but didn't: {success}")
        
    except Exception as e:
        print(f"   ✅ Correctly rejected invalid settings: {e}")
    
    # Test 4: Test render with gallery settings
    print("\n\n4. Testing render with gallery-specific settings:")
    try:
        import asyncio
        
        async def test_render():
            # Test rendering with gallery-specific settings
            result = await channel.render_image(
                resolution=(800, 600), 
                orientation="landscape",
                subchannel_id="family_photos"
            )
            print(f"   ✅ Render successful: {result}")
        
        asyncio.run(test_render())
        
    except Exception as e:
        print(f"   ❌ Error during render test: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Gallery settings test completed!")

if __name__ == "__main__":
    test_gallery_settings()
