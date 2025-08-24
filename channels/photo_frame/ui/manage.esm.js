// x-photo-frame-manager Web Component for Mimir Platform v2.4
class XPhotoFrameManager extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.images = [];
    this.settings = {};
    this.apiBaseUrl = this.getApiBaseUrl();
    this.uploadAreaCollapsed = true;
    this.dragCounter = 0; // Track drag events for proper expand/collapse
    this.galleryId = null; // Gallery context
    this.galleryInfo = null;
  }

  static get observedAttributes() {
    return ['gallery-id'];
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === 'gallery-id') {
      this.galleryId = newValue;
      if (this.isConnected) {
        this.loadData();
      }
    }
  }

  getApiBaseUrl() {
    // Use the server base URL provided by the host platform
    return window.mimirServerBaseUrl || window.location.origin;
  }

  getSettingValue(key, defaultValue = null) {
    // Helper to extract value from new settings format: {type: "string", value: "..."}
    const setting = this.settings[key];
    if (setting && typeof setting === 'object' && 'value' in setting) {
      return setting.value;
    }
    // Fallback for old format or missing setting
    return setting || defaultValue;
  }

  async connectedCallback() {
    await this.loadData();
    this.render();
    this.attachEventListeners();
  }

  async loadData() {
    try {
      if (this.galleryId) {
        // Load gallery-specific content
        const galleryRes = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels/${this.galleryId}`, {
          credentials: 'include'
        });
        
        if (galleryRes.ok) {
          this.galleryInfo = await galleryRes.json();
          
          // Load gallery content
          const contentRes = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels/${this.galleryId}/content`, {
            credentials: 'include'
          });
          
          if (contentRes.ok) {
            const contentData = await contentRes.json();
            this.images = contentData.content || [];
          } else {
            this.images = [];
          }
        } else {
          console.error('Failed to load gallery info');
          this.images = [];
        }
      } else {
        // Load all images (original behavior)
        const imagesRes = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/images`, {
          credentials: 'include'
        });
        this.images = await imagesRes.json();
      }

      // Load settings (same for all galleries for now)
      const settingsRes = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/settings`, {
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
          transition: all 0.3s ease;
          overflow: hidden;
        }
        .upload-area.collapsed {
          max-height: 60px;
          padding: 20px 40px;
        }
        .upload-area.collapsed .upload-content {
          display: none;
        }
        .upload-area.collapsed::before {
          content: "${this.galleryId ? '� Upload to Gallery (click to expand)' : '�📤 Upload Images (click to expand)'}";
          color: #6c757d;
          font-size: 0.9rem;
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
          cursor: move;
        }
        .image-card:hover {
          transform: translateY(-2px);
        }
        .image-card.dragging {
          opacity: 0.5;
          transform: rotate(5deg);
        }
        .image-card.drag-over {
          border: 2px dashed #007bff;
          background: #f0f8ff;
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
          pointer-events: auto;
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
          <h1>${this.galleryInfo ? `📸 ${this.galleryInfo.name}` : 'Photo Frame Management'}</h1>
          ${this.galleryInfo && this.galleryInfo.description ? `<p style="margin: 4px 0 0 0; color: #6c757d; font-size: 0.9rem;">${this.galleryInfo.description}</p>` : ''}
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
                <option value="true" ${this.getSettingValue('slideshow_enabled', true) !== false ? 'selected' : ''}>Enabled</option>
                <option value="false" ${this.getSettingValue('slideshow_enabled', true) === false ? 'selected' : ''}>Disabled</option>
              </select>
            </div>
            <div class="setting-group">
              <label>Image Order</label>
              <select id="order-mode">
                <option value="added" ${this.getSettingValue('order_mode', 'added') === 'added' ? 'selected' : ''}>Date Added</option>
                <option value="random" ${this.getSettingValue('order_mode', 'added') === 'random' ? 'selected' : ''}>Random</option>
                <option value="custom" ${this.getSettingValue('order_mode', 'added') === 'custom' ? 'selected' : ''}>As shown below</option>
              </select>
              <small style="color: #6c757d; font-size: 0.8rem; margin-top: 4px;">
                ${this.getSettingValue('order_mode', 'added') === 'custom' ? 'Drag images below to reorder them' : ''}
              </small>
            </div>
            <div class="setting-group">
              <label>Display Mode</label>
              <select id="crop-mode">
                <option value="smart_crop" ${this.getSettingValue('crop_mode', 'smart_crop') === 'smart_crop' ? 'selected' : ''}>Smart Crop</option>
                <option value="letterbox" ${this.getSettingValue('crop_mode', 'smart_crop') === 'letterbox' ? 'selected' : ''}>Letterbox</option>
                <option value="stretch" ${this.getSettingValue('crop_mode', 'smart_crop') === 'stretch' ? 'selected' : ''}>Stretch</option>
              </select>
            </div>
            <div class="setting-group">
              <label>Update Interval Unit</label>
              <select id="update-interval-unit">
                <option value="seconds" ${this.getSettingValue('update_interval_unit', 'minutes') === 'seconds' ? 'selected' : ''}>Seconds</option>
                <option value="minutes" ${this.getSettingValue('update_interval_unit', 'minutes') === 'minutes' ? 'selected' : ''}>Minutes</option>
                <option value="hours" ${this.getSettingValue('update_interval_unit', 'minutes') === 'hours' ? 'selected' : ''}>Hours</option>
                <option value="days" ${this.getSettingValue('update_interval_unit', 'minutes') === 'days' ? 'selected' : ''}>Days</option>
              </select>
            </div>
            <div class="setting-group">
              <label>Update Interval Value</label>
              <input type="number" id="update-interval-value" min="1" value="${this.getSettingValue('update_interval_value', 30)}" />
            </div>
          </div>
        </div>

        <div class="upload-area ${this.uploadAreaCollapsed ? 'collapsed' : ''}" id="upload-area">
          <div class="upload-content">
            <p><strong>Drop images here or click to upload</strong></p>
            <p>Supported formats: JPG, PNG, GIF</p>
            ${this.galleryId ? `<p style="color: #007bff; font-size: 0.85rem;">📸 Images will be added to this gallery</p>` : ''}
          </div>
          <input type="file" multiple accept="image/*" class="hidden" id="file-input">
        </div>

        <div class="image-grid">
          ${this.getSettingValue('order_mode', 'added') === 'custom' ? '<p style="color: #6c757d; font-size: 0.9rem; margin-bottom: 16px; text-align: center;">💡 Drag and drop images below to change their display order</p>' : ''}
          ${this.images
            .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
            .map(img => `
            <div class="image-card" 
                 data-id="${img.id}" 
                 draggable="true"
                 ondragstart="this.getRootNode().host.handleDragStart(event)"
                 ondragend="this.getRootNode().host.handleDragEnd(event)"
                 ondragover="this.getRootNode().host.handleDragOver(event)"
                 ondrop="this.getRootNode().host.handleDrop(event)">
              <div class="image-preview">
                <img src="${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/assets/uploads/${img.filename}" 
                     alt="${img.title || img.original_name}" 
                     onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjhmOWZhIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzZjNzU3ZCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlIG5vdCBmb3VuZDwvdGV4dD48L3N2Zz4='" />
                <div class="image-overlay">
                  <button class="btn-icon" 
                          onclick="this.getRootNode().host.toggleImage(${img.id})" 
                          onmousedown="event.stopPropagation()"
                          title="${img.enabled ? 'Disable' : 'Enable'}">
                    ${img.enabled ? '👁️' : '🚫'}
                  </button>
                  <button class="btn-icon" 
                          onclick="this.getRootNode().host.deleteImage(${img.id})" 
                          onmousedown="event.stopPropagation()"
                          title="Delete">
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

    // Upload area click to expand or trigger file input
    uploadArea.addEventListener('click', () => {
      if (this.uploadAreaCollapsed) {
        this.uploadAreaCollapsed = false;
        this.render();
        this.attachEventListeners();
      } else {
        fileInput.click();
      }
    });
    
    // Global drag events to handle upload area expansion
    document.addEventListener('dragenter', (e) => {
      if (e.dataTransfer.types.includes('Files')) {
        this.dragCounter++;
        if (this.uploadAreaCollapsed) {
          this.uploadAreaCollapsed = false;
          this.render();
          this.attachEventListeners();
        }
      }
    });

    document.addEventListener('dragleave', (e) => {
      if (e.dataTransfer.types.includes('Files')) {
        this.dragCounter--;
        if (this.dragCounter === 0) {
          setTimeout(() => {
            if (this.dragCounter === 0) {
              this.uploadAreaCollapsed = true;
              this.render();
              this.attachEventListeners();
            }
          }, 100);
        }
      }
    });

    document.addEventListener('drop', (e) => {
      if (e.dataTransfer.types.includes('Files')) {
        this.dragCounter = 0;
      }
    });
    
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
    const settingsElements = [
      'slideshow-enabled', 
      'order-mode', 
      'crop-mode', 
      'update-interval-unit', 
      'update-interval-value'
    ];
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
      const response = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/upload`, {
        method: 'POST',
        body: formData,
        credentials: 'include'
      });

      if (response.ok) {
        const uploadResult = await response.json();
        
        // If we're in a gallery context, assign the uploaded images to this gallery
        if (this.galleryId && uploadResult.uploaded && uploadResult.uploaded.length > 0) {
          const imageIds = uploadResult.uploaded.map(img => img.id.toString());
          
          try {
            await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels/${this.galleryId}/content`, {
              method: 'POST',
              credentials: 'include',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({ 
                content_ids: imageIds, 
                action: 'add' 
              })
            });
          } catch (assignError) {
            console.error('Failed to assign images to gallery:', assignError);
          }
        }
        
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
      crop_mode: this.shadowRoot.getElementById('crop-mode').value,
      update_interval_unit: this.shadowRoot.getElementById('update-interval-unit').value,
      update_interval_value: parseInt(this.shadowRoot.getElementById('update-interval-value').value)
    };

    try {
      const response = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/settings`, {
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
      const response = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/images/${imageId}/toggle`, {
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
        const response = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/images/${imageId}`, {
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

  // Drag and drop methods for image reordering
  handleDragStart(event) {
    const card = event.target.closest('.image-card');
    card.classList.add('dragging');
    event.dataTransfer.setData('text/plain', card.dataset.id);
    event.dataTransfer.effectAllowed = 'move';
  }

  handleDragEnd(event) {
    const card = event.target.closest('.image-card');
    card.classList.remove('dragging');
    
    // Remove drag-over class from all cards
    this.shadowRoot.querySelectorAll('.image-card').forEach(c => {
      c.classList.remove('drag-over');
    });
  }

  handleDragOver(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    
    const card = event.target.closest('.image-card');
    if (card && !card.classList.contains('dragging')) {
      card.classList.add('drag-over');
    }
  }

  async handleDrop(event) {
    event.preventDefault();
    
    const draggedId = event.dataTransfer.getData('text/plain');
    const targetCard = event.target.closest('.image-card');
    
    if (!targetCard || targetCard.dataset.id === draggedId) {
      return;
    }

    const targetId = targetCard.dataset.id;
    
    // Update the order
    await this.updateImageOrder(draggedId, targetId);
    
    // Clean up
    targetCard.classList.remove('drag-over');
  }

  async updateImageOrder(draggedId, targetId) {
    try {
      const response = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/images/reorder`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          dragged_id: parseInt(draggedId),
          target_id: parseInt(targetId)
        }),
        credentials: 'include'
      });

      if (response.ok) {
        await this.refreshData();
      } else {
        console.error('Failed to update image order:', response.statusText);
      }
    } catch (error) {
      console.error('Error updating image order:', error);
    }
  }
}

customElements.define('x-photo-frame-manager', XPhotoFrameManager);
