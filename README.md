# Photo Frame — Mimir Source Plugin

A gallery-based photo slideshow plugin for the [Mimir](https://github.com/ryanlane/mimir) platform. Upload photos, organize them into galleries, and display them on any Mimir-connected screen with configurable ordering, cropping, and update intervals.

**Plugin ID:** `com.epaperframe.photoframe`
**Version:** 1.0.0
**Author:** Ryan Lane

---

## Features

- Multiple galleries with independent image libraries
- Three display modes: smart crop, letterbox, and stretch
- Image ordering: by date added, random, or custom sequence
- Drag-and-drop image upload with thumbnail generation
- Per-image enable/disable without deletion
- Management Web Component with live preview
- Dashboard card widget for quick status overview

---

## Installation

### Via Mimir Plugin Store (recommended)

Open the Mimir UI, go to **Sources**, click **Browse Store**, and search for "Photo Frame". Click **Install**.

### Via git URL

In **Sources → Install Source**, paste:

```
https://github.com/ryanlane/mimir-channel-photoframe.git
```

### Manual

```bash
git clone https://github.com/ryanlane/mimir-channel-photoframe.git
cp -r mimir-channel-photoframe/channels/photo_frame /path/to/mimir-api/channels/
pip install -r channels/photo_frame/requirements.txt
```

Restart (or hot-reload) the Mimir API — the channel is auto-discovered.

---

## Requirements

- Mimir Platform v2.1.0+
- Python 3.8+
- `fastapi`, `pillow`, `sqlalchemy`

---

## Configuration

Settings are managed through the plugin's management interface or via the API at `/api/channels/com.epaperframe.photoframe/settings`.

| Setting | Type | Default | Description |
|---|---|---|---|
| `slideshow_enabled` | boolean | `true` | Rotate through images automatically |
| `order_mode` | string | `"added"` | Image sequence: `added`, `random`, `custom` |
| `crop_mode` | string | `"smart_crop"` | Fit mode: `smart_crop`, `letterbox`, `stretch` |
| `transition_effect` | string | `"fade"` | Transition between images: `fade`, `slide`, `none` |
| `update_interval_value` | integer | `30` | Numeric interval before advancing to next image |
| `update_interval_unit` | string | `"minutes"` | Unit for interval: `seconds`, `minutes`, `hours`, `days` |

---

## API Endpoints

All endpoints are prefixed with `/api/channels/com.epaperframe.photoframe`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/manifest` | Channel capabilities and schema |
| `POST` | `/request_image` | Get the current display image (advances slideshow) |
| `GET` | `/gallery` | List all images in the active gallery |
| `POST` | `/upload` | Upload one or more images (multipart/form-data) |
| `GET` | `/settings` | Get current settings |
| `PUT` | `/settings` | Update settings |
| `GET` | `/status` | Current channel status and active image info |

---

## Management Interface

The plugin registers a full-page management interface in the Mimir UI at the `/photo-frame` route (accessible via the sidebar). From there you can:

- Upload images via drag-and-drop or file picker
- Enable or disable individual images
- Delete images with confirmation
- Switch galleries
- Adjust all settings

A compact dashboard card widget is also available in supported dashboard slots.

---

## File Structure

```
channels/photo_frame/
├── plugin.json          # Channel manifest (id, schema, UI registration)
├── channel.py           # PhotoFrameChannel implementation
├── service.py           # Slideshow and image selection logic
├── requirements.txt     # Python dependencies
├── ui/
│   ├── index.esm.js     # Dashboard card Web Component
│   ├── manage.esm.js    # Full management page Web Component
│   └── styles.css       # Shared component styles
├── assets/              # Static assets (logo, etc.)
└── data/
    ├── photo_frame.db   # SQLite metadata database
    └── thumbs/          # Auto-generated thumbnails
```

---

## Troubleshooting

**Images not showing:** Check that at least one image is enabled in the management interface. Verify the Mimir API can write to the `data/` directory.

**Upload fails:** Confirm the file is a supported format (JPG, JPEG, PNG, GIF) and under 10 MB.

**Web Component not loading:** Check the browser console for JavaScript errors. Ensure the Mimir API is running and accessible at the configured base URL.

**Health check:**
```bash
curl http://localhost:5000/api/channels/com.epaperframe.photoframe/status
```

---

## License

Same terms as the Mimir platform.
