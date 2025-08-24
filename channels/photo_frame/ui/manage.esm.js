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

    const galleryImages = this.state.allImages.filter(img => gallery.contentIds.includes(img.id.toString()));
    
    galleryImages.forEach(image => {
      const card = document.createElement('image-card');
      card.image = image;
      card.isCover = gallery.coverImageId === image.id.toString();
      gridContainer.appendChild(card);
    });
  }

  attachEventListeners() {
    this.shadowRoot.addEventListener('gallery-selected', this.handleGallerySelected.bind(this));
    
    const backBtn = this.shadowRoot.getElementById('back-to-galleries');
    backBtn?.addEventListener('click', this.handleBackToGalleries.bind(this));

    const newGalleryBtn = this.shadowRoot.getElementById('new-gallery-btn');
    newGalleryBtn?.addEventListener('click', this.handleNewGallery.bind(this));

    const createFirstGalleryBtn = this.shadowRoot.getElementById('create-first-gallery-btn');
    createFirstGalleryBtn?.addEventListener('click', this.handleNewGallery.bind(this));

    if (this.state.view === 'gallery-detail') {
      this.attachUploadEventListeners();
      this.shadowRoot.addEventListener('delete-image', this.handleDeleteImage.bind(this));
      this.shadowRoot.addEventListener('set-cover-image', this.handleSetCoverImage.bind(this));
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

    try {
      const res = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/upload`, {
        method: 'POST',
        body: formData,
        credentials: 'include'
      });

      if (res.ok) {
        const uploadResult = await res.json();
        if (this.state.currentGalleryId && uploadResult.uploaded?.length > 0) {
          const imageIds = uploadResult.uploaded.map(img => img.id.toString());
          await this.assignImagesToGallery(imageIds);
        }
        await this.refreshData();
      } else {
        console.error('Upload failed:', res.statusText);
      }
    } catch (error) {
      console.error('Upload error:', error);
    }
  }

  async assignImagesToGallery(imageIds) {
    try {
      await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels/${this.state.currentGalleryId}/content`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content_ids: imageIds, action: 'add' })
      });
    } catch (error) {
      console.error('Failed to assign images to gallery:', error);
    }
  }

  async refreshData() {
    await this.loadInitialData();
    this.render();
    this.attachEventListeners();
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
