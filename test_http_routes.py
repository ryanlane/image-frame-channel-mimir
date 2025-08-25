#!/usr/bin/env python3
"""
Test HTTP-level route functionality
"""

import asyncio
import json
from fastapi.testclient import TestClient
from fastapi import FastAPI
import tempfile
from pathlib import Path
import sys
import os

# Add the channel directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'channels', 'photo_frame'))

async def test_http_routes():
    """Test the routes at HTTP level"""
    
    # Create temp directory and test data
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        data_dir = temp_path / "data"
        data_dir.mkdir(exist_ok=True)
        
        # Create test galleries file
        galleries_file = data_dir / "galleries.json"
        test_galleries = [
            {
                "id": "http_test",
                "name": "HTTP Test Gallery",
                "description": "Test description",
                "contentIds": ["img1"],
                "tags": [],
                "created": "2024-01-01T00:00:00Z",
                "modified": "2024-01-01T00:00:00Z",
                "imageCount": 1,
                "coverImageId": "img1",
                "displaySettings": {
                    "order_mode": "added",
                    "crop_mode": "smart_crop",
                    "update_interval_value": 30,
                    "update_interval_unit": "minutes"
                }
            }
        ]
        
        with open(galleries_file, 'w', encoding='utf-8') as f:
            json.dump(test_galleries, f, indent=2)
        
        from services.gallery_service import GalleryService
        from models.settings import SettingsManager
        from routes.settings import SubchannelSettingsRoutes
        
        # Create services
        gallery_service = GalleryService(temp_path)
        settings_manager = SettingsManager()
        
        # Create route handler and get router
        route_handler = SubchannelSettingsRoutes(gallery_service, settings_manager)
        router = route_handler.create_router()
        
        # Create a test app
        app = FastAPI()
        app.include_router(router)
        
        # Create test client
        client = TestClient(app)
        
        print("HTTP Route Testing")
        print("=" * 40)
        
        # Test 1: GET settings
        print("\n📥 GET /subchannels/http_test/settings")
        response = client.get("/subchannels/http_test/settings")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ GET settings works")
        else:
            print(f"   ❌ GET settings failed: {response.text}")
        
        # Test 2: PUT gallery metadata
        print("\n📤 PUT /subchannels/http_test")
        metadata_payload = {
            "name": "Updated via HTTP",
            "description": "Updated description via HTTP"
        }
        response = client.put("/subchannels/http_test", json=metadata_payload)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        if response.status_code == 200:
            print("   ✅ PUT gallery metadata works")
        else:
            print(f"   ❌ PUT gallery metadata failed")
        
        # Test 3: PUT settings
        print("\n📤 PUT /subchannels/http_test/settings")
        settings_payload = {
            "order_mode": "random",
            "crop_mode": "fit",
            "update_interval_value": 45,
            "update_interval_unit": "seconds"
        }
        response = client.put("/subchannels/http_test/settings", json=settings_payload)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        if response.status_code == 200:
            print("   ✅ PUT settings works")
        else:
            print(f"   ❌ PUT settings failed")
        
        # Test 4: Verify updates
        print("\n🔍 Verification")
        gallery = gallery_service.get_gallery("http_test")
        settings = gallery_service.get_gallery_settings("http_test")
        
        print(f"   Gallery name: {gallery.name}")
        print(f"   Gallery description: {gallery.description}")
        print(f"   Settings crop_mode: {settings.get('crop_mode')}")
        print(f"   Settings order_mode: {settings.get('order_mode')}")
        
        if (gallery.name == "Updated via HTTP" and 
            settings.get('crop_mode') == 'fit' and 
            settings.get('order_mode') == 'random'):
            print("\n🎉 ALL HTTP TESTS PASSED!")
            return True
        else:
            print("\n❌ HTTP tests failed verification")
            return False

if __name__ == "__main__":
    asyncio.run(test_http_routes())
