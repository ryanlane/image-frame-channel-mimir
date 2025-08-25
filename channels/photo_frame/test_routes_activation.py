#!/usr/bin/env python3
"""
Test script to verify the new routes architecture is working correctly.

This script tests key endpoints to ensure the modular routes are functioning
properly after activation.
"""

import asyncio
import sys
from pathlib import Path

# Add the photo frame channel directory to the path
channel_dir = Path(__file__).parent
sys.path.insert(0, str(channel_dir))

async def test_routes_activation():
    """Test that the new routes architecture is working"""
    print("🔧 Testing Photo Frame Channel Routes Architecture...")
    
    try:
        # Import the channel class
        from channel import PhotoFrameChannel
        
        # Create a test instance
        test_channel_dir = "/tmp/test_photo_frame"
        Path(test_channel_dir).mkdir(exist_ok=True)
        
        # Initialize the channel
        channel = PhotoFrameChannel(test_channel_dir)
        
        # Get the router
        router = channel.get_router()
        
        print("✅ Channel initialized successfully")
        print("✅ Router created successfully")
        
        # Check if the router has routes
        routes = router.routes
        print(f"✅ Router has {len(routes)} routes configured")
        
        # List some key routes to verify they're from the new architecture
        route_paths = [route.path for route in routes if hasattr(route, 'path')]
        
        expected_patterns = [
            '/images',
            '/galleries', 
            '/settings',
            '/assets',
            '/admin'
        ]
        
        found_patterns = []
        for pattern in expected_patterns:
            matching_routes = [path for path in route_paths if pattern in path]
            if matching_routes:
                found_patterns.append(pattern)
                print(f"✅ Found {pattern} routes: {len(matching_routes)} endpoints")
        
        if len(found_patterns) >= 4:  # Most route groups should be present
            print("\n🎉 SUCCESS: New routes architecture is ACTIVE!")
            print("📊 Route groups found:", found_patterns)
            return True
        else:
            print("\n❌ ISSUE: Some route groups missing")
            print("📊 Expected:", expected_patterns)
            print("📊 Found:", found_patterns)
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're running from the photo_frame directory")
        return False
        
    except Exception as e:
        print(f"❌ Error testing routes: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_routes_activation())
    sys.exit(0 if result else 1)
