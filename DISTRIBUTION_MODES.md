# Distribution Modes for request_image API

## Overview
The `request_image` endpoint now supports distribution modes to control how images are selected for display clients. This allows for more intelligent image distribution in multi-display scenarios.

## Request Format

```json
{
  "gallery_id": "birds_1",  // Optional: specific gallery/subchannel
  "settings": {
    "subChannelId": "birds_1",
    "resolution": [800, 600],
    "orientation": "landscape",
    "distribution": "current" // NEW: "current" or "new"
  }
}
```

## Distribution Modes

### "current" Mode
- **Purpose**: Return the same image that was last selected for this gallery/channel
- **Use Case**: Multiple displays showing the same content, or ensuring consistency during a display session
- **Behavior**: 
  - Returns the previously selected image if available
  - Falls back to new selection if no previous image or image no longer exists
  - Maintains state per gallery (or globally if no gallery specified)

### "new" Mode (Default)
- **Purpose**: Always select a different image from what was last shown
- **Use Case**: Advancing slideshows, ensuring fresh content on each request
- **Behavior**:
  - Avoids repeating the last selected image if multiple images are available
  - Uses intelligent selection based on channel settings (random, order, etc.)
  - Falls back to any available image if only one image exists

## Response Format

```json
{
  "success": true,
  "image": "base64_encoded_binary_data",
  "filename": "RTL_2499.jpg",
  "image_id": "dca0f0c81e96",
  "gallery_id": "birds_1",
  "total_images": 10,
  "distribution_mode": "current",  // NEW: confirms which mode was used
  "message": "Selected RTL_2499.jpg from 10 images (mode: current)"
}
```

## State Management

The channel maintains distribution state in memory using `_last_selected_by_gallery` dictionary:
- Key: gallery_id (or "default" for no gallery)
- Value: last selected image_id

This ensures:
- "current" requests return consistent images
- "new" requests avoid immediate repetition
- State is maintained separately per gallery

## Backward Compatibility

- If no `distribution` parameter is provided, defaults to "new" mode
- Existing API clients continue to work without changes
- Invalid distribution values fallback to "new" mode

## Examples

### Get the current image for a gallery
```json
POST /api/channels/com.epaperframe.photoframe/request_image
{
  "gallery_id": "family_photos",
  "settings": {
    "distribution": "current"
  }
}
```

### Get a new image for slideshow advancement
```json
POST /api/channels/com.epaperframe.photoframe/request_image
{
  "gallery_id": "family_photos", 
  "settings": {
    "distribution": "new",
    "resolution": [1920, 1080],
    "orientation": "landscape"
  }
}
```

### Global channel (no gallery)
```json
POST /api/channels/com.epaperframe.photoframe/request_image
{
  "settings": {
    "distribution": "current"
  }
}
```

## Implementation Notes

1. **State Persistence**: Current implementation uses in-memory state. For production, consider persisting state to handle service restarts.

2. **Enhanced Selection**: The "new" mode currently uses random selection but could be enhanced to respect order_mode settings from the image service.

3. **Multi-Gallery Support**: Each gallery maintains separate state, allowing different displays to show different content.

4. **Graceful Degradation**: The system gracefully handles edge cases like missing images or empty galleries.