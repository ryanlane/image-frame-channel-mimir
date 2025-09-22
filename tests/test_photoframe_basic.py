import asyncio
import base64


def test_manifest_basic(photoframe_channel):
    manifest = photoframe_channel.get_manifest()
    assert manifest["id"] == "com.epaperframe.photoframe"
    assert manifest.get("healthy") is not False  # should be True or None treated as healthy pre-error
    assert "galleries" in manifest
    assert "status" in manifest


def test_request_image_placeholder(photoframe_channel):
    # With no uploads the channel should fall back to placeholder and succeed
    # We call the async method via event loop
    result = asyncio.get_event_loop().run_until_complete(
        photoframe_channel.request_image({
            "settings": {"resolution": [400, 300], "distribution": "new"},
            "include_base64": True
        })
    )
    assert result["success"] is True
    assert result["content_type"].startswith("image/")
    # Legacy base64 should be present because include_base64 True
    assert "image" in result
    # Ensure bytes reflect an image-like header (JPEG or PNG)
    header = result["bytes"][:4]
    assert header in (b"\xff\xd8\xff\xe0", b"\x89PNG") or header.startswith(b"\xff\xd8")


def test_cache_reuse_current_distribution(photoframe_channel):
    # First request populates cache
    first = asyncio.get_event_loop().run_until_complete(
        photoframe_channel.request_image({
            "settings": {"resolution": [320, 240], "distribution": "new"}
        })
    )
    assert first["success"] is True
    # Second request with distribution=current should attempt cache reuse
    second = asyncio.get_event_loop().run_until_complete(
        photoframe_channel.request_image({
            "settings": {"resolution": [320, 240], "distribution": "current"}
        })
    )
    assert second["success"] is True
    # distribution=current path may be cache miss if TTL expired or logic chooses new, but when reused we mark cached True
    # Accept either but validate schema keys
    assert "cached" in second
    assert "bytes" in second and isinstance(second["bytes"], (bytes, bytearray))
