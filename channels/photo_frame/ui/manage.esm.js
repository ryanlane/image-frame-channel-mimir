// x-photo-frame-manager Web Component for Mimir Platform v2.4
class XPhotoFrameManager extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.images = [];
    this.settings = {};
  }

  async connectedCallback() {
    await this.loadData();
    this.render();
    this.attachEventListeners();
  }

  async loadData() {
    try {
      // Load images
      const imagesRes = await fetch('/api/channels/com.epaperframe.photoframe/images', {
        credentials: 'include'
      });
      this.images = await imagesRes.json();

      // Load settings
      const settingsRes = await fetch('/api/channels/com.epaperframe.photoframe/settings', {
        credentials: 'include'
      });
      this.settings = await settingsRes.json();
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .manager-container {
          padding: 24px;
          background: #f8f9fa;
          min-height: 100vh;
        }
        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 24px;
        }
        .header h1 {
          margin: 0;
          color: #212529;
        }
        .upload-area {
          border: 2px dashed #dee2e6;
          border-radius: 8px;
          padding: 40px;
          text-align: center;
          margin-bottom: 24px;
          background: #ffffff;
          cursor: pointer;
          transition: border-color 0.2s;
        }
        .upload-area:hover {
          border-color: #007bff;
        }
        .upload-area.dragover {
          border-color: #007bff;
          background: #f0f8ff;
        }
        .settings-panel {
          background: #ffffff;
          border-radius: 8px;
          padding: 20px;
          margin-bottom: 24px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .settings-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 16px;
        }
        .setting-group {
          display: flex;
          flex-direction: column;
        }
        .setting-group label {
          font-weight: 500;
          margin-bottom: 4px;
          color: #495057;
        }
        .setting-group select, .setting-group input {
          padding: 8px;
          border: 1px solid #ced4da;
          border-radius: 4px;
          font-size: 0.9rem;
        }
        .image-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 20px;
        }
        .image-card {
          background: #ffffff;
          border-radius: 8px;
          box-shadow: 0 1px 4px rgba(0,0,0,0.1);
          padding: 16px;
          transition: transform 0.2s;
        }
        .image-card:hover {
          transform: translateY(-2px);
        }
        .image-preview {
          position: relative;
          margin-bottom: 12px;
        }
        .image-preview img {
          width: 100%;
          height: 160px;
          object-fit: cover;
          border-radius: 6px;
          background: #f8f9fa;
        }
        .image-overlay {
          position: absolute;
          top: 8px;
          right: 8px;
          display: flex;
          gap: 4px;
        }
        .btn-icon {
          background: rgba(0,0,0,0.7);
          color: white;
          border: none;
          border-radius: 4px;
          padding: 6px;
          cursor: pointer;
          font-size: 14px;
        }
        .btn-icon:hover {
          background: rgba(0,0,0,0.9);
        }
        .image-info h3 {
          margin: 0 0 8px 0;
          font-size: 1rem;
          color: #212529;
        }
        .image-info p {
          margin: 0 0 8px 0;
          color: #6c757d;
          font-size: 0.9rem;
        }
        .image-stats {
          display: flex;
          justify-content: space-between;
          font-size: 0.8rem;
          color: #868e96;
        }
        .btn-primary {
          background: #007bff;
          color: white;
          border: none;
          border-radius: 4px;
          padding: 10px 20px;
          cursor: pointer;
          font-size: 0.9rem;
        }
        .btn-primary:hover {
          background: #0056b3;
        }
        .hidden {
          display: none;
        }
      </style>
      <div class="manager-container">
        <div class="header">
          <h1>Photo Frame Management</h1>
          <button class="btn-primary" onclick="this.getRootNode().host.refreshData()">
            Refresh
          </button>
        </div>
        
        <div class="settings-panel">
          <h3>Settings</h3>
          <div class="settings-grid">
            <div class="setting-group">
              <label>Slideshow Mode</label>
              <select id="slideshow-enabled">
                <option value="true" ${this.settings.slideshow_enabled !== false ? 'selected' : ''}>Enabled</option>
                <option value="false" ${this.settings.slideshow_enabled === false ? 'selected' : ''}>Disabled</option>
              </select>
            </div>
            <div class="setting-group">
              <label>Image Order</label>
              <select id="order-mode">
                <option value="added" ${this.settings.order_mode === 'added' ? 'selected' : ''}>Date Added</option>
                <option value="random" ${this.settings.order_mode === 'random' ? 'selected' : ''}>Random</option>
                <option value="custom" ${this.settings.order_mode === 'custom' ? 'selected' : ''}>Custom Order</option>
              </select>
            </div>
            <div class="setting-group">
              <label>Display Mode</label>
              <select id="crop-mode">
                <option value="smart_crop" ${this.settings.crop_mode === 'smart_crop' ? 'selected' : ''}>Smart Crop</option>
                <option value="letterbox" ${this.settings.crop_mode === 'letterbox' ? 'selected' : ''}>Letterbox</option>
                <option value="stretch" ${this.settings.crop_mode === 'stretch' ? 'selected' : ''}>Stretch</option>
              </select>
            </div>
          </div>
        </div>

        <div class="upload-area" id="upload-area">
          <div>
            <p><strong>Drop images here or click to upload</strong></p>
            <p>Supported formats: JPG, PNG, GIF</p>
          </div>
          <input type="file" multiple accept="image/*" class="hidden" id="file-input">
        </div>

        <div class="image-grid">
          ${this.images.map(img => `
            <div class="image-card" data-id="${img.id}">
              <div class="image-preview">
                <img src="/api/channels/com.epaperframe.photoframe/assets/uploads/${img.filename}" 
                     alt="${img.title || img.original_name}" 
                     onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjhmOWZhIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzZjNzU3ZCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlIG5vdCBmb3VuZDwvdGV4dD48L3N2Zz4='" />
                <div class="image-overlay">
                  <button class="btn-icon" onclick="this.getRootNode().host.toggleImage(${img.id})" title="${img.enabled ? 'Disable' : 'Enable'}">
                    ${img.enabled ? '👁️' : '🚫'}
                  </button>
                  <button class="btn-icon" onclick="this.getRootNode().host.deleteImage(${img.id})" title="Delete">
                    🗑️
                  </button>
                </div>
              </div>
              <div class="image-info">
                <h3>${img.title || img.original_name}</h3>
                <p>${img.description || 'No description'}</p>
                <div class="image-stats">
                  <span>${img.width}×${img.height}</span>
                  <span>Shown: ${img.times_shown || 0} times</span>
                </div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  attachEventListeners() {
    const uploadArea = this.shadowRoot.getElementById('upload-area');
    const fileInput = this.shadowRoot.getElementById('file-input');

    uploadArea.addEventListener('click', () => fileInput.click());
    
    uploadArea.addEventListener('dragover', (e) => {
      e.preventDefault();
      uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
      uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
      e.preventDefault();
      uploadArea.classList.remove('dragover');
      this.handleFiles(e.dataTransfer.files);
    });

    fileInput.addEventListener('change', (e) => {
      this.handleFiles(e.target.files);
    });

    // Settings change listeners
    const settingsElements = ['slideshow-enabled', 'order-mode', 'crop-mode'];
    settingsElements.forEach(id => {
      const element = this.shadowRoot.getElementById(id);
      element?.addEventListener('change', () => this.saveSettings());
    });
  }

  async handleFiles(files) {
    const formData = new FormData();
    
    for (let file of files) {
      if (file.type.startsWith('image/')) {
        formData.append('files', file);
      }
    }

    try {
      const response = await fetch('/api/channels/com.epaperframe.photoframe/upload', {
        method: 'POST',
        body: formData,
        credentials: 'include'
      });

      if (response.ok) {
        await this.refreshData();
      } else {
        console.error('Upload failed:', response.statusText);
      }
    } catch (error) {
      console.error('Upload error:', error);
    }
  }

  async saveSettings() {
    const settings = {
      slideshow_enabled: this.shadowRoot.getElementById('slideshow-enabled').value === 'true',
      order_mode: this.shadowRoot.getElementById('order-mode').value,
      crop_mode: this.shadowRoot.getElementById('crop-mode').value
    };

    try {
      const response = await fetch('/api/channels/com.epaperframe.photoframe/settings', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings),
        credentials: 'include'
      });

      if (response.ok) {
        this.settings = { ...this.settings, ...settings };
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
    }
  }

  async toggleImage(imageId) {
    try {
      const response = await fetch(`/api/channels/com.epaperframe.photoframe/images/${imageId}/toggle`, {
        method: 'POST',
        credentials: 'include'
      });

      if (response.ok) {
        await this.refreshData();
      }
    } catch (error) {
      console.error('Failed to toggle image:', error);
    }
  }

  async deleteImage(imageId) {
    if (confirm('Are you sure you want to delete this image?')) {
      try {
        const response = await fetch(`/api/channels/com.epaperframe.photoframe/images/${imageId}`, {
          method: 'DELETE',
          credentials: 'include'
        });

        if (response.ok) {
          await this.refreshData();
        }
      } catch (error) {
        console.error('Failed to delete image:', error);
      }
    }
  }

  async refreshData() {
    await this.loadData();
    this.render();
    this.attachEventListeners();
  }
}

customElements.define('x-photo-frame-manager', XPhotoFrameManager);
