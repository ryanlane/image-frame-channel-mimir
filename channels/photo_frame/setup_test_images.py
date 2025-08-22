#!/usr/bin/env python3
"""
Photo Frame Channel Setup Script
Initializes the channel with test images and prepares the database.
"""

import os
import sys
import shutil
import hashlib
from pathlib import Path
from PIL import Image

# Add the channel directory to the path so we can import our utilities
channel_dir = Path(__file__).parent
sys.path.insert(0, str(channel_dir))

from utils.database import PhotoFrameDB
from utils.image_processor import ImageProcessor

def setup_test_images():
    """Move test images to the proper uploads directory and register them in the database."""
    
    # Initialize components
    db = PhotoFrameDB(channel_dir / "data" / "photo_frame.db")
    image_processor = ImageProcessor(
        upload_dir=channel_dir / "assets" / "uploads",
        thumb_dir=channel_dir / "data" / "thumbs"
    )
    
    # Ensure directories exist
    (channel_dir / "assets" / "uploads").mkdir(parents=True, exist_ok=True)
    (channel_dir / "data" / "thumbs").mkdir(parents=True, exist_ok=True)
    
    # Find test images in the channel directory
    test_images = []
    for i in range(1, 7):  # image_001 to image_006
        for ext in ['.png', '.jpg', '.jpeg']:
            image_path = channel_dir / f"image_{i:03d}{ext}"
            if image_path.exists():
                test_images.append(image_path)
                break
    
    print(f"Found {len(test_images)} test images to process...")
    
    # Process each test image
    for image_path in test_images:
        try:
            # Generate a safe filename using hash
            with open(image_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()[:12]
            
            # Determine file extension
            ext = image_path.suffix.lower()
            safe_filename = f"image_{file_hash}{ext}"
            dest_path = channel_dir / "assets" / "uploads" / safe_filename
            
            # Copy to uploads directory
            shutil.copy2(image_path, dest_path)
            print(f"Copied {image_path.name} -> {safe_filename}")
            
            # Get image dimensions
            with Image.open(dest_path) as img:
                width, height = img.size
            
            # Add to database
            image_data = {
                "filename": safe_filename,
                "original_name": image_path.name,
                "width": width,
                "height": height
            }
            
            image_id = db.add_image(image_data)
            print(f"Registered image {image_path.name} with ID {image_id}")
            
        except Exception as e:
            print(f"Error processing {image_path.name}: {e}")
    
    # Set default settings
    default_settings = {
        "slideshow_enabled": True,
        "order_mode": "added",
        "crop_mode": "smart_crop"
    }
    
    db.update_settings(default_settings)
    print("Updated default settings")
    
    # Show summary
    total_images = db.get_image_count()
    enabled_images = db.get_enabled_image_count()
    print(f"\nSetup complete!")
    print(f"Total images: {total_images}")
    print(f"Enabled images: {enabled_images}")
    print(f"Database location: {channel_dir}/data/photo_frame.db")
    print(f"Upload directory: {channel_dir}/assets/uploads/")

if __name__ == "__main__":
    setup_test_images()
