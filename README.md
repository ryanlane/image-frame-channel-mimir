# Photo Frame Channel for Mimir Platform

A comprehensive digital photo frame implementation for Mimir Platform v2.4, featuring intelligent image management, slideshow functionality, and a modern web-based management interface.

## Features

### Core Functionality
- **Digital Photo Frame**: Display images on e-ink or other displays
- **Intelligent Slideshow**: Configurable rotation with multiple ordering modes
- **Smart Cropping**: Automated cropping with manual override capabilities
- **Multiple Display Modes**: Smart crop, letterbox, and stretch options
- **Image Management**: Upload, organize, and manage photo collections

### Web Interface
- **Dashboard Integration**: Compact card widget for main dashboard
- **Full Management Interface**: Dedicated page for photo frame administration
- **Drag & Drop Upload**: Modern file upload with progress tracking
- **Real-time Updates**: Live synchronization across all connected clients
- **Responsive Design**: Works on desktop, tablet, and mobile devices

### Technical Features
- **Mimir Platform v2.4**: Full compliance with latest architecture
- **Web Components**: Self-contained UI with Shadow DOM isolation
- **RESTful API**: Comprehensive REST endpoints for all functionality
- **SQLite Database**: Reliable local storage for metadata and settings
- **Image Processing**: Automatic thumbnail generation and optimization
- **WebSocket Integration**: Real-time updates and synchronization

## Installation

### Prerequisites
- Mimir Platform v2.4 or later
- Python 3.8+ with Pillow (PIL) library
- FastAPI for API endpoints

### Setup
1. Copy the entire `channels/photo_frame/` directory to your Mimir Platform channels directory
2. Install Python dependencies:
   ```bash
   pip install -r channels/photo_frame/requirements.txt
   ```
3. The channel will be automatically discovered and mounted by the Mimir Platform
4. Access the management interface at `/photo-frame` in the Mimir web interface

### Directory Structure
```
channels/photo_frame/
├── config.json              # Channel configuration (v2.4 schema)
├── channel.py               # Main channel implementation
├── placeholder.jpg          # Default placeholder image
├── current.jpg              # Current display image
├── requirements.txt         # Python dependencies
├── ui/                      # Web Components
│   ├── index.esm.js         # Dashboard card component
│   ├── manage.esm.js        # Management interface
│   └── styles.css           # Shared styles
├── assets/                  # Static assets
│   ├── logo.svg             # Channel logo
│   └── uploads/             # User-uploaded images
├── data/                    # Channel data
│   ├── photo_frame.db       # SQLite database
│   └── thumbs/              # Generated thumbnails
└── utils/                   # Utility modules
    ├── image_processor.py   # Image processing
    └── database.py          # Database management
```

## Configuration

### Channel Settings
Configure the photo frame behavior through the web interface or API:

- **Slideshow Mode**: Enable/disable automatic image rotation
- **Image Order**: Control image sequence (date added, random, custom)
- **Display Mode**: Choose how images fit the display (smart crop, letterbox, stretch)

### Settings Schema
```json
{
  "slideshow_enabled": true,
  "order_mode": "added",
  "crop_mode": "smart_crop"
}
```

### Update Schedule
Default update interval is 15 minutes, configurable through the channel settings.

## Usage

### Web Interface

#### Dashboard Card
The photo frame automatically appears as a card widget in supported dashboard slots:
- Shows current image with live preview
- Displays statistics (total images, enabled images)
- Provides manual refresh capability
- Integrated with Mimir's theming system

#### Management Interface
Access the full management interface at `/photo-frame`:
- **Upload Images**: Drag and drop multiple images at once
- **Configure Settings**: Adjust slideshow and display preferences
- **Manage Collection**: Enable/disable individual images
- **Preview Images**: View thumbnails with metadata
- **Delete Images**: Remove unwanted images with confirmation

### API Integration

#### Core Endpoints
- `GET /api/channels/com.epaperframe.photoframe/images` - List all images
- `POST /api/channels/com.epaperframe.photoframe/upload` - Upload images
- `GET/PUT /api/channels/com.epaperframe.photoframe/settings` - Manage settings
- `GET /api/channels/com.epaperframe.photoframe/image` - Get current display image

#### Display Client Integration
```javascript
// Example display client implementation
const displayId = 'your-display-id';

async function updateDisplay() {
  const response = await fetch(`/api/displays/${displayId}/current_image`);
  const metadata = await response.json();
  
  if (metadata.image_url) {
    const imageResponse = await fetch(metadata.image_url);
    const blob = await imageResponse.blob();
    displayImage(blob);
  }
}

// Poll for updates based on channel settings
setInterval(updateDisplay, metadata.cache_expires_in * 1000);
```

### Scene Integration
Create scenes that include the photo frame channel:

```json
{
  "name": "Living Room Display",
  "channels": ["com.epaperframe.photoframe"],
  "schedule": {
    "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
    "start": "06:00",
    "end": "23:00"
  }
}
```

## Development

### Channel Protocol Implementation
The channel implements the Mimir v2.4 protocol:

```python
class PhotoFrameChannel:
    @property
    def id(self) -> str
    
    @property 
    def config(self) -> dict
    
    async def render_image(self, resolution, orientation, settings) -> str
    
    async def validate_settings(self, settings) -> dict
    
    def get_status(self) -> dict
    
    def get_router(self) -> APIRouter
```

### Web Component Development
The UI components are implemented as standard Web Components:

```javascript
class XPhotoFrameCard extends HTMLElement {
  connectedCallback() {
    // Initialize component
  }
  
  render() {
    // Update Shadow DOM
  }
}

customElements.define('x-photo-frame-card', XPhotoFrameCard);
```

### Database Schema
The channel uses SQLite with the following main tables:

```sql
-- Images table
CREATE TABLE images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT UNIQUE NOT NULL,
    original_name TEXT NOT NULL,
    title TEXT DEFAULT '',
    description TEXT DEFAULT '',
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    times_shown INTEGER DEFAULT 0,
    last_shown_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    crop_x REAL DEFAULT 0.0,
    crop_y REAL DEFAULT 0.0,
    crop_width REAL DEFAULT 100.0,
    crop_height REAL DEFAULT 100.0
);

-- Settings table
CREATE TABLE channel_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Troubleshooting

### Common Issues

#### Images Not Displaying
1. Check if images are enabled in the management interface
2. Verify file permissions in the `assets/uploads/` directory
3. Check the channel status via `/api/channels/com.epaperframe.photoframe/status`

#### Web Components Not Loading
1. Verify the Mimir Platform supports v2.4 schema
2. Check browser console for JavaScript errors
3. Ensure all UI files are properly served under `/api/channels/com.epaperframe.photoframe/ui/`

#### Database Errors
1. Check file permissions for `data/photo_frame.db`
2. Verify SQLite is properly installed
3. Check available disk space

### Debug Mode
Enable debug logging by setting the log level in your Mimir Platform configuration.

### Health Check
Monitor channel health via:
```bash
curl http://localhost:5000/api/channels/com.epaperframe.photoframe/status
```

## Security Considerations

- **File Validation**: All uploads are validated for image types and size limits
- **Filename Sanitization**: Uploaded files are renamed with secure hash-based names
- **Database Security**: All queries use parameterized statements
- **Settings Validation**: All configuration changes are validated against the schema
- **Web Component Isolation**: UI components use Shadow DOM for style and script isolation

## Contributing

This channel follows the Mimir Platform v2.4 architecture guidelines. When contributing:

1. Follow the established code style
2. Add tests for new functionality
3. Update documentation for API changes
4. Ensure compatibility with the latest Mimir Platform version

## License

This project is licensed under the same terms as the Mimir Platform.

## Support

For issues specific to this channel, please check:
1. The channel status endpoint for runtime errors
2. Browser console for client-side issues
3. Mimir Platform logs for server-side issues

For general Mimir Platform support, refer to the main platform documentation.
