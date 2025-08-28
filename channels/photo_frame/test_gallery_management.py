import sys
from pathlib import Path
# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

import unittest
from pathlib import Path
from channels.photo_frame.channel import PhotoFrameChannel

class TestGalleryManagement(unittest.TestCase):
    def setUp(self):
        # Initialize the PhotoFrameChannel with a test directory
        self.test_dir = Path("/tmp/photo_frame_test")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        # Create a minimal config.json required by PhotoFrameChannel
        config = {
            "id": "com.epaperframe.photoframe",
            "current_image": "current.jpg",
            "placeholder_image": "placeholder.jpg"
        }
        config_path = self.test_dir / "config.json"
        with open(config_path, "w") as f:
            import json
            json.dump(config, f)
        self.channel = PhotoFrameChannel(channel_dir=self.test_dir)

    def tearDown(self):
        # Clean up the test directory after each test (recursively)
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_create_gallery(self):
        # Test creating a gallery
        gallery_data = {"name": "Test Gallery", "description": "A gallery for testing."}
        created_gallery = self.channel.create_subchannel(gallery_data)
        self.assertEqual(created_gallery["name"], "Test Gallery")
        self.assertEqual(created_gallery["description"], "A gallery for testing.")

    def test_delete_gallery(self):
        # Test deleting a gallery
        gallery_data = {"name": "Gallery to Delete", "description": "This will be deleted."}
        created_gallery = self.channel.create_subchannel(gallery_data)
        gallery_id = created_gallery["id"]
        delete_result = self.channel.delete_subchannel(gallery_id)
        self.assertTrue(delete_result)

    def test_update_gallery(self):
        # Test updating a gallery
        gallery_data = {"name": "Gallery to Update", "description": "Initial description."}
        created_gallery = self.channel.create_subchannel(gallery_data)
        gallery_id = created_gallery["id"]

        update_data = {"name": "Updated Gallery", "description": "Updated description."}
        updated_gallery = self.channel.update_subchannel(gallery_id, update_data)
        self.assertEqual(updated_gallery["name"], "Updated Gallery")
        self.assertEqual(updated_gallery["description"], "Updated description.")

if __name__ == "__main__":
    unittest.main()
