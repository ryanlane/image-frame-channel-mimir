import './components/gallery-card.js';
import './components/image-card.js';

// x-photo-frame-manager Web Component for Mimir Platform v2.5
class XPhotoFrameManager extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    
    this.state = {
      view: 'gallery-overview', // 'gallery-overview' or 'gallery-detail'
      galleries: [],
      allImages: [],
      currentGalleryId: null,
      settings: {},
      dragCounter: 0,
      uploadAreaCollapsed: true,
    };

    this.apiBaseUrl = this.getApiBaseUrl();
    
    // Bind event handlers once to prevent duplicate listeners
    this.boundHandleDeleteImage = this.handleDeleteImage.bind(this);
    this.boundHandleSetCoverImage = this.handleSetCoverImage.bind(this);
    this.boundHandleImageReorder = this.handleImageReorder.bind(this);
    this.galleryDetailListenersAttached = false;
    this.processingReorder = false;
  }

  getApiBaseUrl() {
    return window.mimirServerBaseUrl || window.location.origin;
  }

  async connectedCallback() {
    await this.loadInitialData();
    this.render();
    this.attachEventListeners();
  }

  async loadInitialData() {
    try {
      const [galleriesRes, imagesRes, settingsRes] = await Promise.all([
        fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels`, { credentials: 'include' }),
        fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/images`, { credentials: 'include' }),
        fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/settings`, { credentials: 'include' })
      ]);

      // Parse responses with error handling
      const galleriesData = galleriesRes.ok ? await galleriesRes.json() : {};
      const imagesData = imagesRes.ok ? await imagesRes.json() : [];
      const settingsData = settingsRes.ok ? await settingsRes.json() : {};

      // Extract galleries from the subChannels property
      this.state.galleries = Array.isArray(galleriesData?.subChannels) ? galleriesData.subChannels : [];
      this.state.allImages = Array.isArray(imagesData) ? imagesData : [];
      this.state.settings = settingsData || {};

      console.log('Loaded data:', {
        galleries: this.state.galleries.length,
        images: this.state.allImages.length,
        settings: Object.keys(this.state.settings).length
      });

    } catch (error) {
      console.error('Failed to load initial data:', error);
      // Set safe defaults
      this.state.galleries = [];
      this.state.allImages = [];
      this.state.settings = {};
    }
  }

  getSettingValue(key, defaultValue = null) {
    const setting = this.state.settings[key];
    if (setting && typeof setting === 'object' && 'value' in setting) {
      return setting.value;
    }
    return setting || defaultValue;
  }

  render() {
    const viewContainer = document.createElement('div');
    if (this.state.view === 'gallery-overview') {
      viewContainer.innerHTML = this.renderGalleryOverview();
    } else if (this.state.view === 'gallery-detail') {
      viewContainer.innerHTML = this.renderGalleryDetail();
    }

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
        .btn-secondary {
          background: #6c757d;
          color: white;
          border: none;
          border-radius: 4px;
          padding: 8px 16px;
          cursor: pointer;
        }
        .grid-container {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 24px;
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
          content: "📤 Upload Images (click to expand)";
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
        .hidden {
          display: none;
        }
        .first-run-container {
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 60vh;
        }
        .first-run-card {
          background: white;
          border-radius: 12px;
          padding: 48px;
          max-width: 600px;
          text-align: center;
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .first-run-card h2 {
          color: #212529;
          margin-bottom: 16px;
        }
        .feature-list {
          text-align: left;
          margin: 32px 0;
        }
        .feature-item {
          display: flex;
          align-items: flex-start;
          margin-bottom: 24px;
        }
        .feature-icon {
          font-size: 1.5rem;
          margin-right: 16px;
          margin-top: 4px;
        }
        .feature-item strong {
          display: block;
          color: #212529;
          margin-bottom: 4px;
        }
        .feature-item p {
          margin: 0;
          color: #6c757d;
          font-size: 0.9rem;
        }
        .btn-primary.large {
          padding: 16px 32px;
          font-size: 1.1rem;
          margin-top: 16px;
        }
      </style>
      <div class="manager-container">
        ${viewContainer.innerHTML}
      </div>
    `;

    // After HTML is set, populate with custom components
    this.populateComponents();
  }

  renderGalleryOverview() {
    const hasGalleries = this.state.galleries && this.state.galleries.length > 0;
    
    if (!hasGalleries) {
      return `
        <div class="header">
          <h1>🖼️ Photo Frame Galleries</h1>
          <button class="btn-primary" id="new-gallery-btn">Create Your First Gallery</button>
        </div>
        <div class="first-run-container">
          <div class="first-run-card">
            <h2>🎉 Welcome to Photo Frame Manager</h2>
            <p>Get started by creating your first gallery to organize your photos.</p>
            <div class="feature-list">
              <div class="feature-item">
                <span class="feature-icon">📁</span>
                <div>
                  <strong>Organize Photos</strong>
                  <p>Create galleries to group related photos together</p>
                </div>
              </div>
              <div class="feature-item">
                <span class="feature-icon">🎨</span>
                <div>
                  <strong>Set Cover Images</strong>
                  <p>Choose a representative image for each gallery</p>
                </div>
              </div>
              <div class="feature-item">
                <span class="feature-icon">🔄</span>
                <div>
                  <strong>Auto Rotation</strong>
                  <p>Your photo frame will cycle through gallery images</p>
                </div>
              </div>
            </div>
            <button class="btn-primary large" id="create-first-gallery-btn">Create Your First Gallery</button>
          </div>
        </div>
      `;
    }

    return `
      <div class="header">
        <h1>🖼️ Photo Frame Galleries</h1>
        <button class="btn-primary" id="new-gallery-btn">New Gallery</button>
      </div>
      <div class="grid-container" id="gallery-grid">
        <!-- Gallery cards will be inserted here -->
      </div>
    `;
  }

  renderGalleryDetail() {
    const gallery = this.state.galleries.find(g => g.id === this.state.currentGalleryId);
    if (!gallery) return '<h2>Gallery not found</h2>';

    const galleryImages = this.state.allImages.filter(img => gallery.contentIds.includes(img.id.toString()));

    return `
      <div class="header">
        <div>
          <button class="btn-secondary" id="back-to-galleries">← Back to Galleries</button>
          <h1 style="margin-top: 16px;">${gallery.name}</h1>
          <p style="color: #6c757d;">${gallery.description || ''}</p>
        </div>
        <button class="btn-primary" id="gallery-settings-btn">Gallery Settings</button>
      </div>
      
      <div class="upload-area ${this.state.uploadAreaCollapsed ? 'collapsed' : ''}" id="upload-area">
        <div class="upload-content">
          <p><strong>Drop images here or click to upload</strong></p>
          <p>Images will be added to the "${gallery.name}" gallery.</p>
        </div>
        <input type="file" multiple accept="image/*" class="hidden" id="file-input">
      </div>

      <div class="grid-container" id="image-grid">
        <!-- Image cards will be inserted here -->
      </div>
    `;
  }

  // After HTML is set, populate with custom components
  populateComponents() {
    if (this.state.view === 'gallery-overview') {
      this.populateGalleryCards();
    } else if (this.state.view === 'gallery-detail') {
      this.populateImageCards();
      // Attach gallery detail event listeners after image cards are created
      this.attachGalleryDetailEventListeners();
    }
  }

  populateGalleryCards() {
    const gridContainer = this.shadowRoot.getElementById('gallery-grid');
    if (!gridContainer) return;

    // Ensure galleries is an array before iterating
    if (!Array.isArray(this.state.galleries)) {
      console.warn('Galleries is not an array:', this.state.galleries);
      this.state.galleries = [];
      return;
    }

    this.state.galleries.forEach(gallery => {
      const card = document.createElement('gallery-card');
      card.gallery = gallery;
      card.allImages = this.state.allImages;
      gridContainer.appendChild(card);
    });
  }

  populateImageCards() {
    const gridContainer = this.shadowRoot.getElementById('image-grid');
    if (!gridContainer) return;

    const gallery = this.state.galleries.find(g => g.id === this.state.currentGalleryId);
    if (!gallery) return;

    // Ensure allImages is an array and gallery has contentIds
    if (!Array.isArray(this.state.allImages)) {
      console.warn('AllImages is not an array:', this.state.allImages);
      this.state.allImages = [];
      return;
    }

    if (!Array.isArray(gallery.contentIds)) {
      console.warn('Gallery contentIds is not an array:', gallery.contentIds);
      gallery.contentIds = [];
      return;
    }

    // Clear existing cards before adding new ones
    gridContainer.innerHTML = '';

    // Create a map for quick image lookup
    const imageMap = new Map();
    this.state.allImages.forEach(img => imageMap.set(img.id.toString(), img));
    
    // Build gallery images array in the order specified by contentIds
    const galleryImages = gallery.contentIds
      .map(id => imageMap.get(id))
      .filter(img => img !== undefined); // Remove any missing images
    
    console.log('populateImageCards debug:');
    console.log('Gallery contentIds:', gallery.contentIds);
    console.log('All images count:', this.state.allImages.length);
    console.log('Filtered gallery images count:', galleryImages.length);
    console.log('Gallery images order:', galleryImages.map(img => img.id));
    
    galleryImages.forEach((image, index) => {
      const card = document.createElement('image-card');
      card.image = image;
      card.isCover = gallery.coverImageId === image.id.toString();
      
      gridContainer.appendChild(card);
    });
    
    console.log('populateImageCards completed, grid container children:', gridContainer.children.length);
  }

  attachEventListeners() {
    this.shadowRoot.addEventListener('gallery-selected', this.handleGallerySelected.bind(this));
    
    const backBtn = this.shadowRoot.getElementById('back-to-galleries');
    backBtn?.addEventListener('click', this.handleBackToGalleries.bind(this));

    const newGalleryBtn = this.shadowRoot.getElementById('new-gallery-btn');
    newGalleryBtn?.addEventListener('click', this.handleNewGallery.bind(this));

    const createFirstGalleryBtn = this.shadowRoot.getElementById('create-first-gallery-btn');
    createFirstGalleryBtn?.addEventListener('click', this.handleNewGallery.bind(this));

    const gallerySettingsBtn = this.shadowRoot.getElementById('gallery-settings-btn');
    gallerySettingsBtn?.addEventListener('click', this.handleGallerySettings.bind(this));

    if (this.state.view === 'gallery-detail') {
      this.attachUploadEventListeners();
    }
  }

  attachGalleryDetailEventListeners() {
    // Attach event listeners for gallery detail view after components are populated
    console.log('Attaching gallery detail event listeners');
    
    // Only attach if not already attached to prevent duplicates
    if (!this.galleryDetailListenersAttached) {
      this.shadowRoot.addEventListener('delete-image', this.boundHandleDeleteImage);
      this.shadowRoot.addEventListener('set-cover-image', this.boundHandleSetCoverImage);
      this.shadowRoot.addEventListener('image-reorder', this.boundHandleImageReorder);
      this.galleryDetailListenersAttached = true;
      console.log('Gallery detail event listeners attached');
    } else {
      console.log('Gallery detail event listeners already attached, skipping');
    }
  }

  attachUploadEventListeners() {
    const uploadArea = this.shadowRoot.getElementById('upload-area');
    const fileInput = this.shadowRoot.getElementById('file-input');
    if (!uploadArea || !fileInput) return;

    uploadArea.addEventListener('click', () => {
      if (this.state.uploadAreaCollapsed) {
        this.state.uploadAreaCollapsed = false;
        this.render();
        this.attachEventListeners();
      } else {
        fileInput.click();
      }
    });
    
    uploadArea.addEventListener('dragover', e => { e.preventDefault(); uploadArea.classList.add('dragover'); });
    uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
    uploadArea.addEventListener('drop', e => {
      e.preventDefault();
      uploadArea.classList.remove('dragover');
      this.handleFiles(e.dataTransfer.files);
    });
    fileInput.addEventListener('change', e => this.handleFiles(e.target.files));
  }

  async handleFiles(files) {
    const formData = new FormData();
    for (let file of files) {
      if (file.type.startsWith('image/')) {
        formData.append('files', file);
      }
    }

    console.log('Uploading files:', files.length, 'valid images:', [...formData.entries()].length);

    try {
      const res = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/images/upload`, {
        method: 'POST',
        body: formData,
        credentials: 'include'
      });

      console.log('Upload response status:', res.status);
      
      if (res.ok) {
        const uploadResult = await res.json();
        console.log('Upload result:', uploadResult);
        
        if (uploadResult.results && Array.isArray(uploadResult.results)) {
          const successfulUploads = uploadResult.results.filter(r => r.success);
          const failedUploads = uploadResult.results.filter(r => !r.success);
          console.log('Successful uploads:', successfulUploads.length);
          console.log('Failed uploads:', failedUploads.length);
          
          // Debug: show error details for failed uploads
          if (failedUploads.length > 0) {
            console.log('Failed upload details:');
            failedUploads.forEach((upload, index) => {
              console.log(`  ${index + 1}. File: ${upload.filename}, Error: ${upload.error}`);
            });
          }
          
          if (this.state.currentGalleryId && successfulUploads.length > 0) {
            const imageIds = successfulUploads.map(img => img.image_id.toString());
            console.log('Assigning images to gallery:', this.state.currentGalleryId, imageIds);
            try {
              await this.assignImagesToGallery(imageIds);
              console.log('Successfully assigned images to gallery');
            } catch (assignError) {
              console.error('Failed to assign images to gallery:', assignError);
              alert(`Images uploaded but failed to assign to gallery: ${assignError.message}`);
            }
          } else if (!this.state.currentGalleryId) {
            console.log('No current gallery selected, images uploaded but not assigned to any gallery');
          }
        }
        
        await this.refreshData();
      } else {
        const errorText = await res.text();
        console.error('Upload failed with status:', res.status, 'Response:', errorText);
        alert(`Upload failed: ${res.status} ${res.statusText}\n${errorText}`);
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert(`Upload error: ${error.message}`);
    }
  }

  async assignImagesToGallery(imageIds) {
    if (!this.state.currentGalleryId) {
      throw new Error('No gallery selected for image assignment');
    }
    
    if (!imageIds || imageIds.length === 0) {
      throw new Error('No image IDs provided for assignment');
    }
    
    try {
      console.log('Assigning images to gallery:', this.state.currentGalleryId, imageIds);
      const response = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels/${this.state.currentGalleryId}/content`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contentIds: imageIds, action: 'add' })
      });
      
      console.log('Assignment response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Assignment failed:', errorText);
        throw new Error(`Assignment failed: ${response.status} ${errorText}`);
      }
      
      const result = await response.json();
      console.log('Assignment result:', result);
    } catch (error) {
      console.error('Failed to assign images to gallery:', error);
      throw error;
    }
  }

  async refreshData() {
    console.log('Refreshing data...');
    await this.loadInitialData();
    console.log('Data loaded, re-rendering...');
    this.render();
    console.log('Rendered, attaching event listeners...');
    this.attachEventListeners();
    console.log('Refresh complete');
  }

  handleGallerySelected(e) {
    this.state.view = 'gallery-detail';
    this.state.currentGalleryId = e.detail.galleryId;
    this.render();
    this.attachEventListeners();
  }

  handleBackToGalleries() {
    this.state.view = 'gallery-overview';
    this.state.currentGalleryId = null;
    this.galleryDetailListenersAttached = false; // Reset the flag
    this.render();
    this.attachEventListeners();
  }

  async handleNewGallery() {
    const name = prompt("Enter new gallery name:");
    if (!name) return;
    const description = prompt("Enter gallery description (optional):");

    try {
      const res = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description })
      });
      if (res.ok) {
        await this.refreshData();
      } else {
        console.error('Failed to create gallery');
      }
    } catch (error) {
      console.error('Error creating gallery:', error);
    }
  }

  async handleGallerySettings() {
    if (!this.state.currentGalleryId) return;
    
    const gallery = this.state.galleries.find(g => g.id === this.state.currentGalleryId);
    if (!gallery) return;
    
    await this.showSettingsModal(gallery);
  }

  async showSettingsModal(gallery) {
    // First load the gallery-specific settings
    let gallerySettings = {};
    try {
      const response = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels/${gallery.id}/settings`, { credentials: 'include' });
      if (response.ok) {
        const settingsData = await response.json();
        // Extract values from the API format
        gallerySettings = {};
        for (const [key, setting] of Object.entries(settingsData)) {
          gallerySettings[key] = setting.value || setting;
        }
      }
    } catch (error) {
      console.error('Failed to load gallery settings:', error);
      // Use defaults if loading fails
      gallerySettings = {
        order_mode: 'added',
        crop_mode: 'smart_crop',
        update_interval_value: 30,
        update_interval_unit: 'minutes'
      };
    }

    const modal = document.createElement('div');
    modal.className = 'settings-modal';
    modal.innerHTML = `
      <div class="modal-backdrop">
        <div class="modal-content">
          <div class="modal-header">
            <h2>Gallery Settings</h2>
            <button class="close-btn" id="close-modal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="settings-section">
              <h3>Gallery Information</h3>
              <div class="form-group">
                <label for="gallery-name">Gallery Name:</label>
                <input type="text" id="gallery-name" value="${gallery.name}" />
              </div>
              <div class="form-group">
                <label for="gallery-description">Description:</label>
                <textarea id="gallery-description">${gallery.description || ''}</textarea>
              </div>
            </div>
            
            <div class="settings-section">
              <h3>Display Settings</h3>
              <p class="settings-note">These settings apply to this gallery when displayed on photo frames.</p>
              <div class="form-group">
                <label for="order-mode">Image Order:</label>
                <select id="order-mode">
                  <option value="added" ${gallerySettings.order_mode === 'added' ? 'selected' : ''}>Date Added</option>
                  <option value="random" ${gallerySettings.order_mode === 'random' ? 'selected' : ''}>Random</option>
                  <option value="custom" ${gallerySettings.order_mode === 'custom' ? 'selected' : ''}>Custom Order</option>
                </select>
              </div>
              <div class="form-group">
                <label for="crop-mode">Crop Mode:</label>
                <select id="crop-mode">
                  <option value="smart_crop" ${gallerySettings.crop_mode === 'smart_crop' ? 'selected' : ''}>Smart Crop</option>
                  <option value="fit" ${gallerySettings.crop_mode === 'fit' ? 'selected' : ''}>Fit to Screen</option>
                  <option value="fill" ${gallerySettings.crop_mode === 'fill' ? 'selected' : ''}>Fill Screen</option>
                </select>
              </div>
              <div class="form-group-row">
                <div class="form-group">
                  <label for="update-interval-value">Update Every:</label>
                  <input type="number" id="update-interval-value" min="1" value="${gallerySettings.update_interval_value || 30}" />
                </div>
                <div class="form-group">
                  <label for="update-interval-unit">&nbsp;</label>
                  <select id="update-interval-unit">
                    <option value="seconds" ${gallerySettings.update_interval_unit === 'seconds' ? 'selected' : ''}>Seconds</option>
                    <option value="minutes" ${gallerySettings.update_interval_unit === 'minutes' ? 'selected' : ''}>Minutes</option>
                    <option value="hours" ${gallerySettings.update_interval_unit === 'hours' ? 'selected' : ''}>Hours</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" id="cancel-settings">Cancel</button>
            <button class="btn-primary" id="save-settings">Save Settings</button>
          </div>
        </div>
      </div>
    `;

    // Add modal styles
    const style = document.createElement('style');
    style.textContent = `
      .settings-modal {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 1000;
      }
      .modal-backdrop {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .modal-content {
        background: white;
        border-radius: 8px;
        width: 90%;
        max-width: 600px;
        max-height: 90vh;
        overflow-y: auto;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
      }
      .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px 24px;
        border-bottom: 1px solid #dee2e6;
      }
      .modal-header h2 {
        margin: 0;
        color: #212529;
      }
      .close-btn {
        background: none;
        border: none;
        font-size: 24px;
        cursor: pointer;
        color: #6c757d;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .close-btn:hover {
        color: #212529;
      }
      .modal-body {
        padding: 24px;
      }
      .settings-section {
        margin-bottom: 32px;
      }
      .settings-section h3 {
        margin: 0 0 16px 0;
        color: #495057;
        font-size: 1.1rem;
      }
      .settings-note {
        margin: 0 0 16px 0;
        color: #6c757d;
        font-size: 0.9rem;
        font-style: italic;
      }
      .form-group {
        margin-bottom: 16px;
      }
      .form-group-row {
        display: flex;
        gap: 16px;
      }
      .form-group-row .form-group {
        flex: 1;
      }
      .form-group label {
        display: block;
        margin-bottom: 4px;
        font-weight: 500;
        color: #495057;
      }
      .form-group input,
      .form-group select,
      .form-group textarea {
        width: 100%;
        padding: 8px 12px;
        border: 1px solid #ced4da;
        border-radius: 4px;
        font-size: 14px;
        box-sizing: border-box;
      }
      .form-group textarea {
        min-height: 80px;
        resize: vertical;
      }
      .modal-footer {
        padding: 16px 24px;
        border-top: 1px solid #dee2e6;
        display: flex;
        justify-content: flex-end;
        gap: 12px;
      }
    `;

    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(modal);

    // Attach event listeners
    modal.querySelector('#close-modal').addEventListener('click', () => {
      this.shadowRoot.removeChild(modal);
      this.shadowRoot.removeChild(style);
    });

    modal.querySelector('#cancel-settings').addEventListener('click', () => {
      this.shadowRoot.removeChild(modal);
      this.shadowRoot.removeChild(style);
    });

    modal.querySelector('#save-settings').addEventListener('click', () => {
      this.saveSettingsFromModal(gallery, modal, style);
    });

    // Close on backdrop click
    modal.querySelector('.modal-backdrop').addEventListener('click', (e) => {
      if (e.target === e.currentTarget) {
        this.shadowRoot.removeChild(modal);
        this.shadowRoot.removeChild(style);
      }
    });
  }

  async saveSettingsFromModal(gallery, modal, style) {
    try {
      // Get gallery settings
      const galleryName = modal.querySelector('#gallery-name').value;
      const galleryDescription = modal.querySelector('#gallery-description').value;

      // Get photo frame settings for this gallery
      const orderMode = modal.querySelector('#order-mode').value;
      const cropMode = modal.querySelector('#crop-mode').value;
      const updateIntervalValue = modal.querySelector('#update-interval-value').value;
      const updateIntervalUnit = modal.querySelector('#update-interval-unit').value;

      // Save gallery properties
      console.log('Making gallery metadata request to:', `${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels/${gallery.id}`);
      console.log('Gallery metadata payload:', { name: galleryName, description: galleryDescription });
      
      const galleryRes = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels/${gallery.id}`, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          name: galleryName, 
          description: galleryDescription 
        })
      });

      // Save gallery-specific display settings
      const gallerySettings = {
        order_mode: orderMode,
        crop_mode: cropMode,
        update_interval_value: parseInt(updateIntervalValue),
        update_interval_unit: updateIntervalUnit
      };

      console.log('Making gallery settings request to:', `${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels/${gallery.id}/settings`);
      console.log('Gallery settings payload:', gallerySettings);

      const settingsRes = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels/${gallery.id}/settings`, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(gallerySettings)
      });

      if (galleryRes.ok && settingsRes.ok) {
        // Close modal first before refreshing/rendering
        if (modal && modal.parentNode === this.shadowRoot) {
          this.shadowRoot.removeChild(modal);
        }
        if (style && style.parentNode === this.shadowRoot) {
          this.shadowRoot.removeChild(style);
        }
        
        await this.refreshData();
        this.render();
        this.attachEventListeners();
      } else {
        if (!galleryRes.ok) {
          console.error('Failed to update gallery:', galleryRes.status, galleryRes.statusText);
          const galleryError = await galleryRes.text();
          console.error('Gallery error response:', galleryError);
        }
        if (!settingsRes.ok) {
          console.error('Failed to update gallery display settings:', settingsRes.status, settingsRes.statusText);
          const settingsError = await settingsRes.text();
          console.error('Settings error response:', settingsError);
        }
        alert('Failed to save some settings');
        
        // Close modal even on error
        if (modal && modal.parentNode === this.shadowRoot) {
          this.shadowRoot.removeChild(modal);
        }
        if (style && style.parentNode === this.shadowRoot) {
          this.shadowRoot.removeChild(style);
        }
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      console.error('Error details:', error.message, error.stack);
      alert('Error saving settings');
      
      // Close modal even on exception
      if (modal && modal.parentNode === this.shadowRoot) {
        this.shadowRoot.removeChild(modal);
      }
      if (style && style.parentNode === this.shadowRoot) {
        this.shadowRoot.removeChild(style);
      }
    }
  }

  async handleDeleteImage(e) {
    const imageId = e.detail.imageId;
    if (confirm('Are you sure you want to delete this image? This will remove it from all galleries.')) {
      try {
        const res = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/images/${imageId}`, {
          method: 'DELETE',
          credentials: 'include'
        });
        if (res.ok) {
          await this.refreshData();
        } else {
          console.error('Failed to delete image');
        }
      } catch (error) {
        console.error('Error deleting image:', error);
      }
    }
  }

  async handleImageReorder(e) {
    console.log('handleImageReorder called with event:', e);
    console.log('Event target:', e.target);
    console.log('Event currentTarget:', e.currentTarget);
    
    const { draggedImageId, targetImageId } = e.detail;
    const galleryId = this.state.currentGalleryId;
    
    // Prevent duplicate processing of the same event
    if (this.processingReorder) {
      console.log('Already processing a reorder, ignoring duplicate event');
      return;
    }
    
    this.processingReorder = true;
    
    try {
      console.log('Reordering images:', { draggedImageId, targetImageId, galleryId });
      
      const res = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels/${galleryId}/images/reorder`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          dragged_id: draggedImageId, 
          target_id: targetImageId 
        })
      });
      
      if (res.ok) {
        console.log('Images reordered successfully, refreshing gallery data...');
        
        // Add a small delay to ensure the backend has fully saved the changes
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Fetch fresh galleries data
        const galleriesRes = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels`, { 
          credentials: 'include',
          cache: 'no-cache' // Force fresh data, no caching
        });
        if (galleriesRes.ok) {
          const galleriesData = await galleriesRes.json();
          console.log('Fresh galleries data received:', galleriesData);
          
          this.state.galleries = Array.isArray(galleriesData?.subChannels) ? galleriesData.subChannels : [];
          
          // Find the updated gallery
          const updatedGallery = this.state.galleries.find(g => g.id === galleryId);
          console.log('Updated gallery:', updatedGallery);
          console.log('Updated contentIds:', updatedGallery?.contentIds);
          
          // Force a complete refresh of the gallery view
          console.log('Forcing complete gallery view refresh');
          this.galleryDetailListenersAttached = false; // Reset listeners flag
          this.render(); // Complete re-render
          this.attachEventListeners(); // Re-attach all event listeners
          
          console.log('Gallery view refreshed completely');
        } else {
          console.error('Failed to fetch fresh galleries data');
        }
      } else {
        const errorData = await res.text();
        console.error('Failed to reorder images:', errorData);
      }
    } catch (error) {
      console.error('Error reordering images:', error);
    } finally {
      this.processingReorder = false;
    }
  }

  async handleSetCoverImage(e) {
    const imageId = e.detail.imageId;
    const galleryId = this.state.currentGalleryId;
    try {
      const res = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels/${galleryId}`, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cover_image_id: imageId.toString() })
      });
      if (res.ok) {
        await this.refreshData();
      } else {
        console.error('Failed to set cover image');
      }
    } catch (error) {
      console.error('Error setting cover image:', error);
    }
  }
}

customElements.define('x-photo-frame-manager', XPhotoFrameManager);
