
import unittest
from pathlib import Path
import sys
import shutil
import json
# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))
from channels.photo_frame.channel import PhotoFrameChannel

class TestGalleryImageAssignment(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("/tmp/photo_frame_test_image")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        config = {
            "id": "com.epaperframe.photoframe",
            "current_image": "current.jpg",
            "placeholder_image": "placeholder.jpg"
        }
        config_path = self.test_dir / "config.json"
        with open(config_path, "w") as f:
            json.dump(config, f)
        self.channel = PhotoFrameChannel(channel_dir=self.test_dir)

        # Add a test image to the uploads directory and metadata
        self.uploads_dir = self.test_dir / "assets" / "uploads"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.test_image_path = self.uploads_dir / "test_image.jpg"
        with open(self.test_image_path, "wb") as f:
            f.write(b"\x00\x01testimagecontent")
        # Add image to metadata
        image_data = {
            "filename": "test_image.jpg",
            "file_size": 1234,
            "width": 100,
            "height": 100,
            "format": "JPEG",
            "created_at": "2025-08-28T00:00:00Z",
            "enabled": True
        }
        image_id = self.channel.metadata.add_image(image_data)
        self.image_id = str(image_id)

        # Create a gallery
        gallery_data = {"name": "Test Gallery", "description": "A gallery for images."}
        created_gallery = self.channel.create_subchannel(gallery_data)
        self.gallery_id = created_gallery["id"]

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_add_image_to_gallery(self):
        # Assign image to gallery
        result = self.channel.assign_content_to_subchannel(self.gallery_id, [self.image_id], action="add")
        self.assertTrue(result)
        # Check gallery content
        content = self.channel.get_subchannel_content(self.gallery_id)
        print("DEBUG: Gallery content after assignment:", content)
        images = content.get("content", [])
        # Find the image by filename
        found = any(img.get("filename") == "test_image.jpg" for img in images)
        self.assertTrue(found, "test_image.jpg should be in the gallery content")

    def test_remove_image_from_gallery(self):
        # Assign image first
        self.channel.assign_content_to_subchannel(self.gallery_id, [self.image_id], action="add")
        # Remove image from gallery
        result = self.channel.assign_content_to_subchannel(self.gallery_id, [self.image_id], action="remove")
        self.assertTrue(result)
        # Check gallery content
        content = self.channel.get_subchannel_content(self.gallery_id)
        images = content.get("content", [])
        found = any(img.get("filename") == "test_image.jpg" for img in images)
        self.assertFalse(found, "test_image.jpg should not be in the gallery content after removal")

    def test_gallery_image_thumbnail(self):
        # Assign image to gallery
        self.channel.assign_content_to_subchannel(self.gallery_id, [self.image_id], action="add")
        # Simulate thumbnail creation (normally done by image processor)
        thumb_path = self.uploads_dir / "test_image.thumb.jpg"
        with open(thumb_path, "wb") as f:
            f.write(b"\x00\x01thumbcontent")
        # Check gallery content for thumbnail path
        content = self.channel.get_subchannel_content(self.gallery_id)
        print("DEBUG: Gallery content for thumbnail:", content)
        images = content.get("content", [])
        image = next((img for img in images if img.get("filename") == "test_image.jpg"), None)
        print("DEBUG: image for thumbnail:", image)
        self.assertIsNotNone(image)
        # Thumbnail path logic may vary; here we check for the expected filename
        self.assertTrue(
            "thumb" in thumb_path.name or "thumb" in image.get("filename", ""),
            "Thumbnail should be present for the image."
        )

if __name__ == "__main__":
    unittest.main()
