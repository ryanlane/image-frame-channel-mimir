#!/usr/bin/env python3
"""
Photo Frame Channel Integration Test

This script specifically tests the photo frame channel integration with the 
centralized Mimir API after our updates.

Focus areas:
1. Channel discovery and configuration
2. Subchannel (gallery) operations with correct endpoints
3. Image upload and management
4. Thumbnail serving (the original issue!)
5. Content assignment to subchannels
6. API endpoint compatibility

Expected Channel ID: com.epaperframe.photoframe
Expected Directory: /var/opt/mimir/mimir-api/channels/photo_frame/
"""

import json
import time
import requests
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from io import BytesIO
from PIL import Image as PILImage


class PhotoFrameIntegrationTester:
    """Focused test suite for photo frame channel integration"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.channel_id = "com.epaperframe.photoframe"  # Correct channel ID
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, message: str = "", data: Any = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": time.time()
        }
        if data:
            result["data"] = data
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
    
    def make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with error handling"""
        try:
            response = requests.request(method, url, **kwargs)
            return response
        except Exception as e:
            print(f"❌ Request failed: {e}")
            raise
    
    def test_channel_discovery(self) -> bool:
        """Test that the photo frame channel is properly discovered"""
        response = self.make_request('GET', f"{self.base_url}/api/channels")
        
        if response.status_code == 200:
            try:
                data = response.json()
                channels = data.get('channels', [])
                
                # Find photo frame channel
                photo_frame_channel = None
                for channel in channels:
                    if channel.get('id') == self.channel_id:
                        photo_frame_channel = channel
                        break
                
                if photo_frame_channel:
                    self.log_test(
                        "channel_discovery", 
                        True, 
                        f"Found photo frame channel: {photo_frame_channel.get('name')}",
                        {
                            "channel_id": photo_frame_channel.get('id'),
                            "channel_dir": photo_frame_channel.get('channelDir'),
                            "name": photo_frame_channel.get('name')
                        }
                    )
                    return True
                else:
                    self.log_test("channel_discovery", False, f"Photo frame channel not found among {len(channels)} channels")
                    return False
                    
            except json.JSONDecodeError:
                self.log_test("channel_discovery", False, "Invalid JSON response")
                return False
        else:
            self.log_test("channel_discovery", False, f"HTTP {response.status_code}")
            return False
    
    def test_channel_config(self) -> Dict[str, Any]:
        """Test channel configuration endpoint"""
        response = self.make_request('GET', f"{self.base_url}/api/channels/{self.channel_id}/config")
        
        if response.status_code == 200:
            try:
                config = response.json()
                expected_id = self.channel_id
                actual_id = config.get('id')
                
                if actual_id == expected_id:
                    self.log_test(
                        "channel_config", 
                        True, 
                        f"Config loaded correctly: {config.get('name')}",
                        {"version": config.get('version'), "id": actual_id}
                    )
                    return config
                else:
                    self.log_test("channel_config", False, f"ID mismatch: expected {expected_id}, got {actual_id}")
                    return {}
                    
            except json.JSONDecodeError:
                self.log_test("channel_config", False, "Invalid JSON response")
                return {}
        else:
            self.log_test("channel_config", False, f"HTTP {response.status_code}")
            return {}
    
    def test_subchannel_operations(self) -> List[Dict[str, Any]]:
        """Test subchannel (gallery) operations"""
        # List existing subchannels
        response = self.make_request('GET', f"{self.base_url}/api/channels/{self.channel_id}/subchannels")
        
        if response.status_code == 200:
            try:
                data = response.json()
                subchannels = data.get('subchannels', [])
                self.log_test(
                    "list_subchannels", 
                    True, 
                    f"Found {len(subchannels)} existing subchannels",
                    {"count": len(subchannels)}
                )
                
                # Test subchannel details if any exist
                if subchannels:
                    first_subchannel = subchannels[0]
                    subchannel_id = first_subchannel.get('id')
                    
                    # Test individual subchannel access
                    detail_response = self.make_request(
                        'GET', 
                        f"{self.base_url}/api/channels/{self.channel_id}/subchannels/{subchannel_id}"
                    )
                    
                    if detail_response.status_code == 200:
                        detail_data = detail_response.json()
                        self.log_test(
                            "subchannel_detail", 
                            True, 
                            f"Retrieved subchannel: {detail_data.get('name')}",
                            {"subchannel_id": subchannel_id, "image_count": detail_data.get('imageCount', 0)}
                        )
                    else:
                        self.log_test("subchannel_detail", False, f"HTTP {detail_response.status_code}")
                
                return subchannels
                
            except json.JSONDecodeError:
                self.log_test("list_subchannels", False, "Invalid JSON response")
                return []
        else:
            self.log_test("list_subchannels", False, f"HTTP {response.status_code}")
            return []
    
    def test_subchannel_images(self, subchannel_id: str) -> List[Dict[str, Any]]:
        """Test subchannel image listing"""
        response = self.make_request(
            'GET', 
            f"{self.base_url}/api/channels/{self.channel_id}/subchannels/{subchannel_id}/images"
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                images = data.get('images', [])
                self.log_test(
                    "subchannel_images", 
                    True, 
                    f"Found {len(images)} images in subchannel {subchannel_id}",
                    {"count": len(images), "subchannel_id": subchannel_id}
                )
                return images
                
            except json.JSONDecodeError:
                self.log_test("subchannel_images", False, "Invalid JSON response")
                return []
        else:
            self.log_test("subchannel_images", False, f"HTTP {response.status_code}")
            return []
    
    def test_subchannel_thumbnail(self, subchannel_id: str, image_id: str) -> bool:
        """Test subchannel thumbnail serving - THE CRITICAL TEST!"""
        response = self.make_request(
            'GET', 
            f"{self.base_url}/api/channels/{self.channel_id}/subchannels/{subchannel_id}/images/{image_id}/thumbnail"
        )
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if content_type.startswith('image/'):
                self.log_test(
                    "subchannel_thumbnail", 
                    True, 
                    f"Thumbnail served successfully ({len(response.content)} bytes)",
                    {
                        "content_type": content_type, 
                        "size": len(response.content),
                        "subchannel_id": subchannel_id,
                        "image_id": image_id
                    }
                )
                return True
            else:
                self.log_test("subchannel_thumbnail", False, f"Wrong content type: {content_type}")
                return False
        else:
            self.log_test("subchannel_thumbnail", False, f"HTTP {response.status_code}")
            return False
    
    def test_image_upload(self) -> List[str]:
        """Test image upload functionality"""
        # Create a test image
        img = PILImage.new('RGB', (400, 300), color=(0, 128, 255))
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        test_image_data = buffer.getvalue()
        
        files = [('files', ('integration_test.jpg', BytesIO(test_image_data), 'image/jpeg'))]
        
        response = self.make_request(
            'POST', 
            f"{self.base_url}/api/channels/{self.channel_id}/images/upload",
            files=files
        )
        
        if response.status_code == 200:
            try:
                result = response.json()
                results = result.get('results', [])
                successful_uploads = [r for r in results if r.get('success')]
                
                image_ids = [str(r.get('image_id')) for r in successful_uploads if r.get('image_id')]
                
                self.log_test(
                    "image_upload", 
                    len(successful_uploads) > 0, 
                    f"Uploaded {len(successful_uploads)}/{len(results)} images",
                    {"uploaded_image_ids": image_ids}
                )
                
                return image_ids
                
            except json.JSONDecodeError:
                self.log_test("image_upload", False, "Invalid JSON response")
                return []
        else:
            self.log_test("image_upload", False, f"HTTP {response.status_code}")
            return []
    
    def test_content_assignment(self, subchannel_id: str, image_ids: List[str]) -> bool:
        """Test content assignment to subchannel"""
        if not image_ids:
            self.log_test("content_assignment", False, "No images available for assignment")
            return False
        
        response = self.make_request(
            'POST', 
            f"{self.base_url}/api/channels/{self.channel_id}/subchannels/{subchannel_id}/content",
            json={
                "contentIds": image_ids[:2],  # Assign first 2 images
                "action": "add"
            }
        )
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('success'):
                    self.log_test(
                        "content_assignment", 
                        True, 
                        f"Assigned {len(image_ids[:2])} images to subchannel {subchannel_id}",
                        {"subchannel_id": subchannel_id, "assigned_count": len(image_ids[:2])}
                    )
                    return True
                else:
                    self.log_test("content_assignment", False, "API returned success=false")
                    return False
                    
            except json.JSONDecodeError:
                self.log_test("content_assignment", False, "Invalid JSON response")
                return False
        else:
            self.log_test("content_assignment", False, f"HTTP {response.status_code}")
            return False
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run the complete photo frame integration test suite"""
        print("🖼️  PHOTO FRAME CHANNEL INTEGRATION TEST")
        print("=" * 60)
        print(f"📡 API Base URL: {self.base_url}")
        print(f"🆔 Channel ID: {self.channel_id}")
        print("=" * 60)
        
        start_time = time.time()
        
        # Test 1: Channel Discovery
        channel_found = self.test_channel_discovery()
        if not channel_found:
            print("❌ Channel discovery failed - cannot continue")
            return self.get_summary(time.time() - start_time)
        
        # Test 2: Channel Configuration
        config = self.test_channel_config()
        if not config:
            print("❌ Channel configuration failed - cannot continue")
            return self.get_summary(time.time() - start_time)
        
        # Test 3: Subchannel Operations
        subchannels = self.test_subchannel_operations()
        
        # Test 4: Image Upload
        uploaded_image_ids = self.test_image_upload()
        
        # Test 5: Content Assignment and Thumbnail Testing
        if subchannels and uploaded_image_ids:
            first_subchannel_id = subchannels[0].get('id')
            
            # Assign content
            content_assigned = self.test_content_assignment(first_subchannel_id, uploaded_image_ids)
            
            if content_assigned:
                # Test subchannel images after assignment
                subchannel_images = self.test_subchannel_images(first_subchannel_id)
                
                # Test thumbnail serving (the critical test!)
                if subchannel_images:
                    # Use the first uploaded image for thumbnail test
                    self.test_subchannel_thumbnail(first_subchannel_id, uploaded_image_ids[0])
        
        total_time = time.time() - start_time
        return self.get_summary(total_time)
    
    def get_summary(self, total_time: float) -> Dict[str, Any]:
        """Generate test summary"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        summary = {
            "channel_id": self.channel_id,
            "total_time_seconds": round(total_time, 2),
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": round((passed_tests / total_tests * 100) if total_tests > 0 else 0, 1),
            "detailed_results": self.test_results
        }
        
        print("\n" + "=" * 60)
        print("📊 PHOTO FRAME INTEGRATION TEST SUMMARY")
        print("=" * 60)
        print(f"⏱️  Total Time: {summary['total_time_seconds']}s")
        print(f"🧪 Tests: {passed_tests}/{total_tests} passed")
        print(f"📈 Success Rate: {summary['success_rate']}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS ({failed_tests}):")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test']}: {result['message']}")
        
        # Specific integration status
        print(f"\n🔍 INTEGRATION STATUS:")
        discovery_ok = any(r['test'] == 'channel_discovery' and r['success'] for r in self.test_results)
        config_ok = any(r['test'] == 'channel_config' and r['success'] for r in self.test_results)
        thumbnail_ok = any(r['test'] == 'subchannel_thumbnail' and r['success'] for r in self.test_results)
        
        print(f"   📡 Channel Discovery: {'✅ OK' if discovery_ok else '❌ FAILED'}")
        print(f"   ⚙️  Configuration: {'✅ OK' if config_ok else '❌ FAILED'}")
        print(f"   🖼️  Thumbnail Serving: {'✅ OK' if thumbnail_ok else '❌ FAILED'}")
        
        if discovery_ok and config_ok and thumbnail_ok:
            print(f"\n🎉 PHOTO FRAME INTEGRATION: SUCCESSFUL!")
        else:
            print(f"\n⚠️  PHOTO FRAME INTEGRATION: NEEDS ATTENTION")
        
        return summary


def main():
    """Main test runner"""
    base_url = "http://oak:5000"  # Default to oak server
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"🚀 Starting Photo Frame Channel Integration Test")
    print(f"📡 Target API: {base_url}")
    
    try:
        from PIL import Image as PILImage
    except ImportError:
        print("❌ PIL (Pillow) not available. Cannot run image upload tests.")
        print("   Install with: pip install Pillow")
        return 1
    
    tester = PhotoFrameIntegrationTester(base_url)
    summary = tester.run_comprehensive_test()
    
    # Exit with appropriate code
    if summary["failed"] == 0:
        print(f"\n🎉 All integration tests passed!")
        return 0
    else:
        print(f"\n⚠️  {summary['failed']} integration tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
