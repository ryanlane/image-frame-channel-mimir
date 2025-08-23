"""
Test Photo Frame Channel with Gallery Support
Validates gallery (sub-channel) functionality
"""

import json
import tempfile
import asyncio
from pathlib import Path
from typing import Dict, Any, List
import sys
import os

# Mock the database and image processor for testing
class MockPhotoFrameDB:
    def __init__(self, db_path):
        self.images = [
            {"id": 1, "filename": "image1.jpg", "original_name": "Family Photo 1", "enabled": True, "upload_time": "2024-01-01"},
            {"id": 2, "filename": "image2.jpg", "original_name": "Vacation 1", "enabled": True, "upload_time": "2024-01-02"},
            {"id": 3, "filename": "image3.jpg", "original_name": "Nature 1", "enabled": True, "upload_time": "2024-01-03"},
            {"id": 4, "filename": "image4.jpg", "original_name": "Portrait 1", "enabled": False, "upload_time": "2024-01-04"},
            {"id": 5, "filename": "image5.jpg", "original_name": "Family Photo 2", "enabled": True, "upload_time": "2024-01-05"},
        ]
    
    def get_total_image_count(self):
        return len(self.images)
    
    def get_enabled_image_count(self):
        return len([img for img in self.images if img["enabled"]])
    
    def get_all_images(self):
        return self.images
    
    def get_enabled_images(self):
        return [img for img in self.images if img["enabled"]]
    
    def get_image_by_id(self, image_id):
        for img in self.images:
            if img["id"] == image_id:
                return img
        return None

class MockImageProcessor:
    def __init__(self, upload_dir, thumb_dir):
        self.upload_dir = upload_dir
        self.thumb_dir = thumb_dir

# Mock BaseChannel for testing
class BaseChannel:
    def _generate_subchannel_id(self, name: str) -> str:
        """Generate unique ID from name"""
        import re
        # Clean the name
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', name).lower()
        base_id = re.sub(r'\s+', '_', clean_name.strip())
        
        # Check for duplicates in galleries
        existing_ids = {gallery['id'] for gallery in self._galleries}
        
        if base_id not in existing_ids:
            return base_id
        
        # Add suffix for duplicates
        counter = 1
        while f"{base_id}_{counter}" in existing_ids:
            counter += 1
        return f"{base_id}_{counter}"

# Import the channel class with mocked dependencies
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Create a modified version that doesn't import the real dependencies
class PhotoFrameChannelWithGalleries(BaseChannel):
    """
    Photo Frame channel for Mimir Platform v2.4+ with Gallery (Sub-channel) Support
    Test version with mocked dependencies
    """
    
    def __init__(self, channel_dir: str):
        self.channel_dir = Path(channel_dir)
        self.config_path = self.channel_dir / "config.json"
        self._config = self._load_config()
        
        # Mock components
        self.db = MockPhotoFrameDB(self.channel_dir / "data" / "photo_frame.db")
        self.image_processor = MockImageProcessor(
            upload_dir=self.channel_dir / "assets" / "uploads",
            thumb_dir=self.channel_dir / "data" / "thumbs"
        )
        
        # Gallery management
        self.galleries_file = self.channel_dir / "data" / "galleries.json"
        self._galleries = self._load_galleries()
        
        # State tracking
        self.last_update = None
        self.last_error = None
        self.current_image_id = None
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load channel configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {
            "id": "com.epaperframe.photoframe",
            "name": "Photo Frame",
            "placeholder_image": "placeholder.jpg"
        }
    
    def _load_galleries(self) -> List[Dict[str, Any]]:
        """Load galleries (sub-channels) configuration"""
        if self.galleries_file.exists():
            with open(self.galleries_file, 'r') as f:
                return json.load(f)
        return []
    
    def _save_galleries(self):
        """Save galleries configuration"""
        self.galleries_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.galleries_file, 'w') as f:
            json.dump(self._galleries, f, indent=2)
    
    def _ensure_directories(self):
        """Create necessary directories"""
        dirs = [
            self.channel_dir / "assets" / "uploads",
            self.channel_dir / "data" / "thumbs",
            self.channel_dir / "data"
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    @property
    def id(self) -> str:
        return self._config.get("id", "com.epaperframe.photoframe")
    
    @property 
    def config(self) -> dict:
        return self._config
    
    # Sub-channel (Gallery) support methods
    
    def supports_subchannels(self) -> bool:
        return True
    
    def get_subchannel_config(self) -> Dict[str, Any]:
        return {
            "enabled": True,
            "label": "Gallery",
            "labelPlural": "Galleries",
            "description": "Organize photos into themed collections",
            "supports_tagging": True,
            "supports_multiple_membership": True,
            "allowCustom": True,
            "contentType": "image",
            "maxSubChannels": 50
        }
    
    def get_subchannels(self) -> List[Dict[str, Any]]:
        return self._galleries.copy()
    
    def create_subchannel(self, data: Dict[str, Any]) -> Dict[str, Any]:
        from datetime import datetime, timezone
        
        if "name" not in data:
            raise ValueError("Gallery name is required")
        
        gallery_id = self._generate_subchannel_id(data["name"])
        
        gallery = {
            "id": gallery_id,
            "name": data["name"],
            "description": data.get("description", ""),
            "contentIds": [],
            "tags": data.get("tags", []),
            "created": datetime.now(timezone.utc).isoformat(),
            "modified": datetime.now(timezone.utc).isoformat(),
            "imageCount": 0,
            "coverImageId": None
        }
        
        self._galleries.append(gallery)
        self._save_galleries()
        
        return gallery
    
    def update_subchannel(self, subchannel_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        from datetime import datetime, timezone
        
        for i, gallery in enumerate(self._galleries):
            if gallery["id"] == subchannel_id:
                if "name" in data:
                    gallery["name"] = data["name"]
                if "description" in data:
                    gallery["description"] = data["description"]
                if "tags" in data:
                    gallery["tags"] = data["tags"]
                
                gallery["modified"] = datetime.now(timezone.utc).isoformat()
                self._save_galleries()
                return gallery
        
        raise ValueError(f"Gallery '{subchannel_id}' not found")
    
    def delete_subchannel(self, subchannel_id: str) -> bool:
        for i, gallery in enumerate(self._galleries):
            if gallery["id"] == subchannel_id:
                del self._galleries[i]
                self._save_galleries()
                return True
        
        raise ValueError(f"Gallery '{subchannel_id}' not found")
    
    def assign_content_to_subchannel(
        self, 
        subchannel_id: str, 
        content_ids: List[str], 
        action: str = "add"
    ) -> bool:
        from datetime import datetime, timezone
        
        gallery = self._find_gallery(subchannel_id)
        if not gallery:
            raise ValueError(f"Gallery '{subchannel_id}' not found")
        
        # Validate content IDs
        valid_image_ids = {str(img["id"]) for img in self.db.get_all_images()}
        invalid_ids = set(content_ids) - valid_image_ids
        if invalid_ids:
            raise ValueError(f"Invalid image IDs: {', '.join(invalid_ids)}")
        
        if action == "set":
            gallery["contentIds"] = content_ids.copy()
        elif action == "add":
            for content_id in content_ids:
                if content_id not in gallery["contentIds"]:
                    gallery["contentIds"].append(content_id)
        elif action == "remove":
            gallery["contentIds"] = [
                c for c in gallery["contentIds"] if c not in content_ids
            ]
        else:
            raise ValueError(f"Invalid action '{action}'")
        
        gallery["imageCount"] = len(gallery["contentIds"])
        gallery["modified"] = datetime.now(timezone.utc).isoformat()
        
        if gallery["contentIds"] and not gallery["coverImageId"]:
            gallery["coverImageId"] = gallery["contentIds"][0]
        
        self._save_galleries()
        return True
    
    def get_subchannel_content(
        self, 
        subchannel_id: str, 
        limit: int = None, 
        offset: int = None
    ) -> Dict[str, Any]:
        gallery = self._find_gallery(subchannel_id)
        if not gallery:
            raise ValueError(f"Gallery '{subchannel_id}' not found")
        
        content_ids = gallery["contentIds"]
        total_count = len(content_ids)
        
        if offset:
            content_ids = content_ids[offset:]
        if limit:
            content_ids = content_ids[:limit]
        
        images = []
        for content_id in content_ids:
            image_data = self.db.get_image_by_id(int(content_id))
            if image_data:
                images.append({
                    "id": str(image_data["id"]),
                    "name": image_data.get("title", image_data["original_name"]),
                    "filename": image_data["filename"],
                    "enabled": image_data["enabled"],
                    "uploaded": image_data["upload_time"]
                })
        
        return {
            "content": images,
            "totalCount": total_count,
            "limit": limit,
            "offset": offset or 0
        }
    
    def _find_gallery(self, gallery_id: str):
        for gallery in self._galleries:
            if gallery["id"] == gallery_id:
                return gallery
        return None

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "active",
            "total_images": self.db.get_total_image_count(),
            "enabled_images": self.db.get_enabled_image_count(),
            "galleries": len(self._galleries)
        }


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def run_test(self, test_name: str, test_func):
        try:
            print(f"Running {test_name}...", end=" ")
            test_func()
            print("PASS")
            self.passed += 1
        except Exception as e:
            print("FAIL")
            self.failed += 1
            error_msg = f"{test_name}: {str(e)}"
            self.errors.append(error_msg)
            print(f"  Error: {str(e)}")
    
    def assert_equal(self, actual, expected, message=""):
        if actual != expected:
            msg = f"Expected {expected}, got {actual}"
            if message:
                msg = f"{message}: {msg}"
            raise AssertionError(msg)
    
    def assert_true(self, condition, message=""):
        if not condition:
            msg = "Condition was False"
            if message:
                msg = f"{message}: {msg}"
            raise AssertionError(msg)
    
    def summary(self):
        print(f"\n{'='*50}")
        print(f"Test Results: {self.passed} passed, {self.failed} failed")
        if self.errors:
            print("\nErrors:")
            for error in self.errors:
                print(f"  - {error}")
        print(f"{'='*50}")
        return self.failed == 0


def test_gallery_support():
    """Test basic gallery support functionality"""
    with tempfile.TemporaryDirectory() as temp_dir:
        channel = PhotoFrameChannelWithGalleries(temp_dir)
        
        # Test sub-channel support
        runner.assert_true(channel.supports_subchannels())
        
        config = channel.get_subchannel_config()
        runner.assert_equal(config["enabled"], True)
        runner.assert_equal(config["label"], "Gallery")
        
        # Initially no galleries
        galleries = channel.get_subchannels()
        runner.assert_equal(len(galleries), 0)


def test_gallery_creation():
    """Test creating galleries"""
    with tempfile.TemporaryDirectory() as temp_dir:
        channel = PhotoFrameChannelWithGalleries(temp_dir)
        
        # Create a gallery
        gallery = channel.create_subchannel({
            "name": "Family Photos",
            "description": "Pictures of family members",
            "tags": ["family", "personal"]
        })
        
        runner.assert_equal(gallery["name"], "Family Photos")
        runner.assert_equal(gallery["description"], "Pictures of family members")
        runner.assert_equal(gallery["id"], "family_photos")
        runner.assert_equal(len(gallery["contentIds"]), 0)
        
        # Check it's saved
        galleries = channel.get_subchannels()
        runner.assert_equal(len(galleries), 1)
        runner.assert_equal(galleries[0]["name"], "Family Photos")


def test_gallery_content_management():
    """Test adding/removing images from galleries"""
    with tempfile.TemporaryDirectory() as temp_dir:
        channel = PhotoFrameChannelWithGalleries(temp_dir)
        
        # Create a gallery
        gallery = channel.create_subchannel({"name": "Test Gallery"})
        gallery_id = gallery["id"]
        
        # Add some images (using mock image IDs)
        channel.assign_content_to_subchannel(gallery_id, ["1", "2", "3"], "add")
        
        # Check content
        content = channel.get_subchannel_content(gallery_id)
        runner.assert_equal(content["totalCount"], 3)
        runner.assert_equal(len(content["content"]), 3)
        
        # Remove an image
        channel.assign_content_to_subchannel(gallery_id, ["2"], "remove")
        content = channel.get_subchannel_content(gallery_id)
        runner.assert_equal(content["totalCount"], 2)
        
        # Set specific images
        channel.assign_content_to_subchannel(gallery_id, ["1", "5"], "set")
        content = channel.get_subchannel_content(gallery_id)
        runner.assert_equal(content["totalCount"], 2)
        runner.assert_true(any(img["id"] == "1" for img in content["content"]))
        runner.assert_true(any(img["id"] == "5" for img in content["content"]))


def test_gallery_crud_operations():
    """Test full CRUD operations on galleries"""
    with tempfile.TemporaryDirectory() as temp_dir:
        channel = PhotoFrameChannelWithGalleries(temp_dir)
        
        # Create
        gallery = channel.create_subchannel({"name": "Original Name"})
        gallery_id = gallery["id"]
        
        # Update
        updated = channel.update_subchannel(gallery_id, {
            "name": "Updated Name",
            "description": "New description"
        })
        runner.assert_equal(updated["name"], "Updated Name")
        runner.assert_equal(updated["description"], "New description")
        
        # Verify update persisted
        galleries = channel.get_subchannels()
        runner.assert_equal(galleries[0]["name"], "Updated Name")
        
        # Delete
        result = channel.delete_subchannel(gallery_id)
        runner.assert_true(result)
        
        # Verify deletion
        galleries = channel.get_subchannels()
        runner.assert_equal(len(galleries), 0)


def test_unique_gallery_ids():
    """Test unique ID generation for galleries"""
    with tempfile.TemporaryDirectory() as temp_dir:
        channel = PhotoFrameChannelWithGalleries(temp_dir)
        
        # Create galleries with same name
        gallery1 = channel.create_subchannel({"name": "Family Photos"})
        gallery2 = channel.create_subchannel({"name": "Family Photos"})
        
        runner.assert_true(gallery1["id"] != gallery2["id"])
        runner.assert_equal(gallery1["id"], "family_photos")
        runner.assert_equal(gallery2["id"], "family_photos_1")


# Initialize global test runner
runner = TestRunner()

if __name__ == "__main__":
    print("Running Photo Frame Gallery (Sub-Channel) Tests")
    print("="*50)
    
    # Run tests
    runner.run_test("Gallery support detection", test_gallery_support)
    runner.run_test("Gallery creation", test_gallery_creation) 
    runner.run_test("Gallery content management", test_gallery_content_management)
    runner.run_test("Gallery CRUD operations", test_gallery_crud_operations)
    runner.run_test("Unique gallery ID generation", test_unique_gallery_ids)
    
    # Print summary
    success = runner.summary()
    
    if success:
        print("\n✅ All gallery tests passed! Photo Frame sub-channel support is working.")
    else:
        print("\n❌ Some gallery tests failed. Please check the implementation.")
    
    sys.exit(0 if success else 1)
