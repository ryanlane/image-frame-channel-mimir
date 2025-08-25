#!/usr/bin/env python3
"""
Test upload endpoint directly
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import os
from fastapi.testclient import TestClient
from fastapi import FastAPI
import io

# Add the channel directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'channels', 'photo_frame'))

def test_upload_endpoint():
    """Test the upload endpoint directly"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create necessary directories
        data_dir = temp_path / "data"
        assets_dir = temp_path / "assets" / "uploads"
        data_dir.mkdir(exist_ok=True)
        assets_dir.mkdir(parents=True, exist_ok=True)
        
        # Create empty galleries.json
        galleries_file = data_dir / "galleries.json"
        with open(galleries_file, 'w') as f:
            f.write("[]")
        
        from services.gallery_service import GalleryService
        from services.image_service import ImageService
        from services.storage_service import StorageService
        from services.metadata_service import MetadataService
        from services.image_processor import ImageProcessor
        from routes.images import ImagesRoutes
        
        # Create services
        gallery_service = GalleryService(temp_path)
        storage_service = StorageService(temp_path)
        metadata_service = MetadataService(temp_path)
        image_processor = ImageProcessor()
        image_service = ImageService(storage_service, metadata_service, image_processor)
        
        # Create route handler
        route_handler = ImagesRoutes(image_service, gallery_service, storage_service, metadata_service, image_processor)
        router = route_handler.create_router()
        
        # Create test app
        app = FastAPI()
        app.include_router(router)
        
        # Create test client
        client = TestClient(app)
        
        print("Upload Endpoint Test")
        print("=" * 30)
        
        # Create a fake image file for testing
        fake_image_content = b"fake image content for testing"
        files = {
            'files': ('test.jpg', io.BytesIO(fake_image_content), 'image/jpeg')
        }
        
        print("\n📤 Testing POST /images/upload")
        response = client.post("/images/upload", files=files)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 200:
            print("   ✅ Upload endpoint is accessible")
        elif response.status_code == 422:
            print("   ⚠️ Upload endpoint accessible but validation failed (expected with fake image)")
        else:
            print(f"   ❌ Upload endpoint failed: {response.status_code}")
        
        # Also test if the router is set up correctly
        print(f"\n🔍 Router info:")
        print(f"   Prefix: {router.prefix}")
        print(f"   Routes: {len(router.routes)}")
        for route in router.routes:
            if hasattr(route, 'path') and 'upload' in route.path:
                print(f"   - {route.methods} {route.path}")
        
        return response.status_code in [200, 422]  # Both are acceptable for this test

if __name__ == "__main__":
    test_upload_endpoint()
