#!/usr/bin/env python3
"""
Photo Frame Channel Test Script
Tests the core functionality of the photo frame channel.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the channel directory to the path
channel_dir = Path(__file__).parent
sys.path.insert(0, str(channel_dir))

# Import the channel
from channel import PhotoFrameChannel

async def test_channel():
    """Test the photo frame channel functionality."""
    
    print("=== Photo Frame Channel Test ===\n")
    
    # Initialize the channel
    channel = PhotoFrameChannel(str(channel_dir))
    print(f"Channel ID: {channel.id}")
    print(f"Channel Name: {channel.config['name']}")
    print(f"Channel Version: {channel.config['version']}")
    
    # Test channel status
    print("\n--- Channel Status ---")
    status = channel.get_status()
    for key, value in status.items():
        print(f"{key}: {value}")
    
    # Test settings validation
    print("\n--- Settings Validation ---")
    test_settings = {
        "slideshow_enabled": True,
        "order_mode": "random", 
        "crop_mode": "letterbox"
    }
    
    errors = await channel.validate_settings(test_settings)
    if errors:
        print("Validation errors:")
        for key, error in errors.items():
            print(f"  {key}: {error}")
    else:
        print("Settings validation passed!")
    
    # Test image rendering
    print("\n--- Image Rendering Test ---")
    try:
        # Test with different resolutions and orientations
        test_cases = [
            ((800, 600), "landscape"),
            ((600, 800), "portrait"),
            ((1920, 1080), "landscape")
        ]
        
        for resolution, orientation in test_cases:
            print(f"Testing {resolution} {orientation}...")
            image_path = await channel.render_image(
                resolution=resolution,
                orientation=orientation,
                settings=test_settings
            )
            print(f"  Generated: {image_path}")
            
            # Check if file exists
            full_path = channel_dir / image_path
            if full_path.exists():
                size = full_path.stat().st_size
                print(f"  File size: {size} bytes")
            else:
                print(f"  Warning: File not found at {full_path}")
    
    except Exception as e:
        print(f"Error during image rendering: {e}")
    
    # Test database operations
    print("\n--- Database Test ---")
    db = channel.db
    images = db.get_all_images()
    print(f"Total images in database: {len(images)}")
    
    if images:
        print("Sample image data:")
        sample = images[0]
        for key, value in sample.items():
            print(f"  {key}: {value}")
    
    # Test settings operations
    print("\n--- Settings Test ---")
    current_settings = db.get_settings()
    print("Current settings:", current_settings)
    
    # Update settings
    new_settings = {"slideshow_enabled": False, "order_mode": "added"}
    db.update_settings(new_settings)
    
    updated_settings = db.get_settings()
    print("Updated settings:", updated_settings)
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    try:
        asyncio.run(test_channel())
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
