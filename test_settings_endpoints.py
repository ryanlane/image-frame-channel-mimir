#!/usr/bin/env python3
"""
Test script to verify Photo Frame Channel settings endpoints
Tests the new /settings GET and PUT endpoints according to API documentation.
"""

import sys
import json
from pathlib import Path

# Add channels directory to path for testing
channels_dir = Path(__file__).parent / "channels" / "photo_frame"
sys.path.insert(0, str(channels_dir))

from channel import PhotoFrameChannel
from fastapi import FastAPI
from fastapi.testclient import TestClient

def test_settings_endpoints():
    """Test the Photo Frame Channel settings endpoints"""
    print("🧪 Testing Photo Frame Channel Settings Endpoints")
    print("=" * 60)
    
    # Initialize channel
    channel = PhotoFrameChannel(str(channels_dir))
    app = FastAPI()
    
    # Mount the router
    router = channel.get_router()
    if router:
        app.include_router(router, prefix="/api/channels/com.epaperframe.photoframe")
    
    client = TestClient(app)
    
    # Test 1: GET /settings
    print("\n📋 Test 1: GET /settings")
    response = client.get("/api/channels/com.epaperframe.photoframe/settings")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        settings = response.json()
        print(f"Settings: {json.dumps(settings, indent=2)}")
        
        # Verify expected fields
        expected_fields = ["slideshow_enabled", "order_mode", "crop_mode"]
        for field in expected_fields:
            if field in settings:
                print(f"✅ {field}: {settings[field]}")
            else:
                print(f"❌ Missing field: {field}")
    else:
        print(f"❌ GET /settings failed: {response.text}")
    
    # Test 2: PUT /settings with valid data
    print("\n📝 Test 2: PUT /settings (valid data)")
    test_settings = {
        "slideshow_enabled": False,
        "order_mode": "random",
        "crop_mode": "letterbox"
    }
    
    response = client.put(
        "/api/channels/com.epaperframe.photoframe/settings",
        json=test_settings
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        if result.get("success"):
            print("✅ Settings updated successfully")
        else:
            print("❌ Update failed")
    else:
        print(f"❌ PUT /settings failed: {response.text}")
    
    # Test 3: Verify settings were saved
    print("\n🔍 Test 3: Verify settings persistence")
    response = client.get("/api/channels/com.epaperframe.photoframe/settings")
    
    if response.status_code == 200:
        settings = response.json()
        print(f"Updated settings: {json.dumps(settings, indent=2)}")
        
        # Check if our test values were saved
        for key, expected_value in test_settings.items():
            if settings.get(key) == expected_value:
                print(f"✅ {key}: {expected_value} (persisted)")
            else:
                print(f"❌ {key}: expected {expected_value}, got {settings.get(key)}")
    else:
        print(f"❌ Failed to verify settings: {response.text}")
    
    # Test 4: PUT /settings with invalid data
    print("\n❌ Test 4: PUT /settings (invalid data)")
    invalid_settings = {
        "order_mode": "invalid_mode",
        "crop_mode": "invalid_crop"
    }
    
    response = client.put(
        "/api/channels/com.epaperframe.photoframe/settings",
        json=invalid_settings
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 400:
        result = response.json()
        print(f"Expected validation error: {json.dumps(result, indent=2)}")
        if "errors" in result:
            print("✅ Validation errors properly returned")
        else:
            print("❌ Missing validation errors")
    else:
        print(f"❌ Expected 400 status for invalid data, got {response.status_code}")
    
    # Test 5: Test hardware endpoint (should still work)
    print("\n🖥️  Test 5: GET /hardware (existing endpoint)")
    response = client.get("/api/channels/com.epaperframe.photoframe/hardware")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        hardware = response.json()
        print(f"Hardware info: {json.dumps(hardware, indent=2)}")
        print("✅ Hardware endpoint working")
    else:
        print(f"❌ Hardware endpoint failed: {response.text}")
    
    print("\n" + "=" * 60)
    print("🏁 Settings endpoints testing completed")

if __name__ == "__main__":
    test_settings_endpoints()
