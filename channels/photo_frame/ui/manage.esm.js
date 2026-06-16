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
        fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/internal/settings`, { credentials: 'include' })
      ]);

      // Parse responses with error handling
      const galleriesData = galleriesRes.ok ? await galleriesRes.json() : [];
      const imagesData = imagesRes.ok ? await imagesRes.json() : [];
      const settingsData = settingsRes.ok ? await settingsRes.json() : {};

      // The subchannels endpoint returns an array directly
      this.state.galleries = Array.isArray(galleriesData) ? galleriesData : [];
      
      // For each gallery, we need to fetch the individual gallery details to get content_ids
      // since the list endpoint doesn't include them
      if (this.state.galleries.length > 0) {
        const galleryDetailsPromises = this.state.galleries.map(gallery =>
          fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels/${gallery.id}`, { credentials: 'include' })
            .then(res => res.ok ? res.json() : null)
            .catch(() => null)
        );
        
        const galleryDetails = await Promise.all(galleryDetailsPromises);
        
        // Merge the detailed data back into galleries
        this.state.galleries = this.state.galleries.map((gallery, index) => {
          const details = galleryDetails[index];
          if (details) {
            // Convert snake_case to camelCase for consistency
            return {
              ...gallery,
              contentIds: details.content_ids || [],
              coverImageId: details.cover_image_id || null
            };
          }
          return {
            ...gallery,
            contentIds: [],
            coverImageId: null
          };
        });
      }
      
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
          color: var(--color-text, #1A1A1A);
        }
        .manager-container {
          padding: 24px;
          background: var(--color-background, #F3F8F6);
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
          color: var(--color-text, #1A1A1A);
        }
        /* Button styles (match host web UI pattern: .btn + variants) */
        .btn {
          --_btn-bg: var(--color-surface, #E2EDE9);
          --_btn-fg: var(--color-text, #1A1A1A);
          --_btn-border: var(--color-border, #D0DDD7);
          --_btn-bg-hover: var(--color-surface-hover, #D6E7E1);
          --_btn-border-hover: var(--color-border, #D0DDD7);
          --_btn-bg-active: var(--_btn-bg-hover);
          --_btn-border-active: var(--_btn-border-hover);

          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: var(--spacing-sm, 0.5rem);
          padding: var(--spacing-sm, 0.5rem) var(--spacing-md, 1rem);
          border: 1px solid var(--_btn-border);
          border-radius: var(--radius-sm, 6px);
          background: var(--_btn-bg);
          color: var(--_btn-fg);
          font-family: inherit;
          font-size: 0.875rem;
          font-weight: 500;
          cursor: pointer;
          transition: background .18s ease, border-color .18s ease, color .18s ease, transform .1s ease, opacity .18s ease;
          user-select: none;
        }
        .btn:hover:not(:disabled) {
          background: var(--_btn-bg-hover);
          border-color: var(--_btn-border-hover);
          opacity: 0.95;
        }
        .btn:active:not(:disabled) {
          transform: translateY(1px);
          background: var(--_btn-bg-active);
          border-color: var(--_btn-border-active);
        }
        .btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .btn-primary {
          --_btn-bg: var(--color-success, #036600);
          --_btn-fg: var(--color-text-on-dark, #FFFFFF);
          --_btn-border: var(--color-primary, #036600);
          --_btn-bg-hover: var(--color-primary-hover, var(--color-success, #036600));
          --_btn-border-hover: var(--color-primary-hover, var(--color-primary, #036600));
        }
        .btn-secondary {
          --_btn-bg: var(--color-surface, #E2EDE9);
          --_btn-fg: var(--color-text, #1A1A1A);
          --_btn-border: var(--color-border, #D0DDD7);
          --_btn-bg-hover: var(--color-background-alt, #EAF2EE);
          --_btn-border-hover: var(--color-border, #D0DDD7);
        }
        .btn-danger {
          --_btn-bg: var(--color-error, #C62828);
          --_btn-fg: var(--color-text-on-dark, #FFFFFF);
          --_btn-border: var(--color-error, #C62828);
          --_btn-bg-hover: color-mix(in srgb, var(--color-error, #C62828) 80%, white);
          --_btn-border-hover: var(--color-error, #C62828);
        }
        .btn-sm {
          padding: var(--spacing-xs, 0.25rem) var(--spacing-sm, 0.5rem);
          font-size: 0.75rem;
        }
        .btn-lg {
          padding: var(--spacing-md, 1rem) var(--spacing-lg, 1.5rem);
          font-size: 1rem;
        }
        .btn-block {
          width: 100%;
        }
        .grid-container {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 24px;
        }
        .upload-area {
          border: 2px dashed var(--color-primary, #036600);
          border-radius: 8px;
          padding: 40px;
          text-align: center;
          margin-bottom: 24px;
          background: var(--color-surface, #ffffff);
          color: var(--color-text, #1A1A1A);
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
          color: var(--upload-area-collapsed-text-color, var(--color-text-tertiary, #6c757d));
          font-size: 0.9rem;
        }
        .upload-area:hover {
          border-color: var(--color-accent, #00C851);
        }
        .upload-area.dragover {
          border-color: var(--color-accent-hover, var(--color-accent, #00C851));
          background: var(--color-background-alt, #EAF2EE);
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
          background: var(--color-surface, #ffffff);
          border-radius: 12px;
          padding: 48px;
          max-width: 600px;
          text-align: center;
          box-shadow: var(--elevation-2, 0 4px 12px rgba(0,0,0,0.1));
        }
        .first-run-card h2 {
          color: var(--color-text, #1A1A1A);
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
          color: var(--color-text, #1A1A1A);
          margin-bottom: 4px;
        }
        .feature-item p {
          margin: 0;
          color: var(--color-text-secondary, #3D4A44);
          font-size: 0.9rem;
        }
        .muted {
          color: var(--color-text-tertiary, #64706A);
        }
        .btn-lg {
          padding: 16px 32px;
          font-size: 1.1rem;
          margin-top: 16px;
        }
        #upload-progress {
          margin: 0 0 16px 0;
          padding: 12px 16px;
          background: var(--color-surface, #fff);
          border: 1px solid var(--color-border, #D0DDD7);
          border-radius: 6px;
        }
        .progress-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }
        .progress-label {
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--color-text-secondary, #3D4A44);
        }
        .progress-count {
          font-size: 0.8rem;
          color: var(--color-text-tertiary, #64706A);
        }
        .progress-track {
          height: 6px;
          background: var(--color-background-alt, #EAF2EE);
          border-radius: 3px;
          overflow: hidden;
        }
        .progress-fill {
          height: 100%;
          background: var(--color-accent, #00C851);
          border-radius: 3px;
          transition: width 0.25s ease;
        }
        .upload-area.uploading {
          pointer-events: none;
          opacity: 0.7;
        }
        @keyframes card-appear {
          from { opacity: 0; transform: scale(0.92); }
          to   { opacity: 1; transform: scale(1); }
        }
        .image-card-entering {
          animation: card-appear 0.2s ease forwards;
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
          <button class="btn btn-primary" id="new-gallery-btn">Create Your First Gallery</button>
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
            <button class="btn btn-primary btn-lg" id="create-first-gallery-btn">Create Your First Gallery</button>
          </div>
        </div>
      `;
    }

    return `
      <div class="header">
        <h1>🖼️ Photo Frame Galleries</h1>
        <button class="btn btn-primary" id="new-gallery-btn">New Gallery</button>
      </div>
      <div class="grid-container" id="gallery-grid">
        <!-- Gallery cards will be inserted here -->
      </div>
      <template id="gallery-card-template">
        <div class="gallery-card-actions">
          <button class="btn btn-danger delete-gallery-btn" data-gallery-id="">🗑️ Delete</button>
        </div>
      </template>
    `;
  }

  renderGalleryDetail() {
    const gallery = this.state.galleries.find(g => g.id === this.state.currentGalleryId);
    if (!gallery) return '<h2>Gallery not found</h2>';

    const galleryImages = this.state.allImages.filter(img => gallery.contentIds.includes(img.id.toString()));

    return `
      <div class="header">
        <div>
          <button class="btn btn-secondary" id="back-to-galleries">← Back to Galleries</button>
          <h1 style="margin-top: 16px;">${gallery.name}</h1>
          <p class="muted">${gallery.description || ''}</p>
        </div>
        <button class="btn btn-primary" id="gallery-settings-btn">Gallery Settings</button>
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

    // Clear existing cards
    gridContainer.innerHTML = '';

    this.state.galleries.forEach(gallery => {
      const card = document.createElement('gallery-card');
      card.gallery = gallery;
      card.allImages = this.state.allImages;
      gridContainer.appendChild(card);

      // Add delete button to each card
      const actionsDiv = document.createElement('div');
      actionsDiv.className = 'gallery-card-actions';
      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'btn btn-danger delete-gallery-btn';
      deleteBtn.textContent = '🗑️ Delete';
      deleteBtn.setAttribute('data-gallery-id', gallery.id);
      deleteBtn.addEventListener('click', (e) => this.handleDeleteGallery(e, gallery.id));
      actionsDiv.appendChild(deleteBtn);
      card.appendChild(actionsDiv);
    });
  }
  async handleDeleteGallery(e, galleryId) {
    e.stopPropagation();
    if (!galleryId) return;
    if (!confirm('Are you sure you want to delete this gallery? This cannot be undone.')) return;
    try {
      const res = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels/${galleryId}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      if (res.ok) {
        await this.refreshData();
      } else {
        const errorText = await res.text();
        alert('Failed to delete gallery: ' + errorText);
      }
    } catch (error) {
      alert('Error deleting gallery: ' + error.message);
    }
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
    
    galleryImages.forEach((image, index) => {
      const card = document.createElement('image-card');
      card.image = image;
      card.isCover = gallery.coverImageId === image.id.toString();
      // Add remove button
      const removeBtn = document.createElement('button');
      removeBtn.className = 'btn btn-secondary remove-image-btn';
      removeBtn.textContent = 'Remove from Gallery';
      removeBtn.style.marginTop = '8px';
      removeBtn.addEventListener('click', (e) => this.handleRemoveImageFromGallery(e, image.id, gallery.id));
      card.appendChild(removeBtn);
      gridContainer.appendChild(card);
    });
  }
  async handleRemoveImageFromGallery(e, imageId, galleryId) {
    e.stopPropagation();
    if (!galleryId || !imageId) return;
    if (!confirm('Remove this image from the gallery?')) return;
    try {
      const res = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels/${galleryId}/content`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contentIds: [imageId], action: 'remove' })
      });
      if (res.ok) {
        await this.refreshData();
      } else {
        const errorText = await res.text();
        alert('Failed to remove image: ' + errorText);
      }
    } catch (error) {
      alert('Error removing image: ' + error.message);
    }
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
    if (this._uploading) return;

    const imageFiles = [...files].filter(f => f.type.startsWith('image/'));
    if (!imageFiles.length) return;

    this._uploading = true;
    const total = imageFiles.length;
    let completed = 0;
    const uploadedIds = [];

    this.state.uploadAreaCollapsed = false;
    this._showUploadProgress(total);
    const uploadArea = this.shadowRoot.getElementById('upload-area');
    uploadArea?.classList.add('uploading');

    const gallery = this.state.galleries.find(g => g.id === this.state.currentGalleryId);

    // Create preview cards for every file immediately — before any upload starts
    const pendingCards = new Map(); // File → { card, previewUrl }
    for (const file of imageFiles) {
      const previewUrl = URL.createObjectURL(file);
      const card = this._appendPreviewCard(file.name, gallery, previewUrl);
      pendingCards.set(file, { card, previewUrl });
    }

    // Upload all files in parallel; update each card in place as it resolves
    await Promise.all(imageFiles.map(async (file) => {
      const { card, previewUrl } = pendingCards.get(file);
      const formData = new FormData();
      formData.append('files', file);
      try {
        const res = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/images/upload`, {
          method: 'POST',
          body: formData,
          credentials: 'include',
        });
        if (res.ok) {
          const result = await res.json();
          for (const img of (result.results || []).filter(r => r.success)) {
            const imageObj = { id: img.image_id, filename: img.filename };
            this.state.allImages.push(imageObj);
            if (gallery) {
              gallery.contentIds = [...(gallery.contentIds || []), img.image_id.toString()];
            }
            uploadedIds.push(img.image_id.toString());
            // Update the existing card in place: swap in real data, remove spinner
            // Keep previewSrc until refreshData re-renders with the server thumbnail
            card.uploading = false;
            card.image = imageObj;
          }
        } else {
          console.error('Upload failed for', file.name, res.status);
          card.remove();
        }
      } catch (err) {
        console.error('Upload error for', file.name, err);
        card.remove();
      }
      completed++;
      this._updateUploadProgress(completed, total);
    }));

    if (this.state.currentGalleryId && uploadedIds.length > 0) {
      try {
        await this.assignImagesToGallery(uploadedIds);
      } catch (err) {
        console.error('Failed to assign images to gallery:', err);
      }
    }

    // Revoke preview object URLs before the full re-render
    for (const { previewUrl } of pendingCards.values()) {
      URL.revokeObjectURL(previewUrl);
    }

    this._hideUploadProgress();
    uploadArea?.classList.remove('uploading');
    this._uploading = false;

    await this.refreshData();
  }

  _showUploadProgress(total) {
    const existing = this.shadowRoot.getElementById('upload-progress');
    if (existing) existing.remove();

    const bar = document.createElement('div');
    bar.id = 'upload-progress';
    bar.innerHTML = `
      <div class="progress-header">
        <span class="progress-label">Uploading images…</span>
        <span class="progress-count">0 of ${total}</span>
      </div>
      <div class="progress-track"><div class="progress-fill" style="width:0%"></div></div>
    `;

    const grid = this.shadowRoot.getElementById('image-grid');
    const uploadArea = this.shadowRoot.getElementById('upload-area');
    if (grid) {
      grid.insertAdjacentElement('beforebegin', bar);
    } else if (uploadArea) {
      uploadArea.insertAdjacentElement('afterend', bar);
    }
  }

  _updateUploadProgress(completed, total) {
    const bar = this.shadowRoot.getElementById('upload-progress');
    if (!bar) return;
    const pct = Math.round((completed / total) * 100);
    bar.querySelector('.progress-count').textContent = `${completed} of ${total}`;
    bar.querySelector('.progress-label').textContent =
      completed < total ? 'Uploading images…' : `${completed} of ${total} uploaded`;
    bar.querySelector('.progress-fill').style.width = `${pct}%`;
  }

  _hideUploadProgress() {
    const bar = this.shadowRoot.getElementById('upload-progress');
    if (bar) {
      bar.querySelector('.progress-label').textContent = 'Upload complete';
      bar.querySelector('.progress-fill').style.width = '100%';
      // refreshData() re-renders shortly after, which removes this element
    }
  }

  _appendPreviewCard(filename, gallery, previewUrl) {
    const grid = this.shadowRoot.getElementById('image-grid');
    if (!grid) return null;

    const card = document.createElement('image-card');
    card.className = 'image-card-entering';
    // Set previewSrc and uploading before image so the first render uses them
    card.previewSrc = previewUrl;
    card.uploading = true;
    card.image = { id: `pending-${Date.now()}`, filename };
    card.isCover = false;

    const removeBtn = document.createElement('button');
    removeBtn.className = 'btn btn-secondary remove-image-btn';
    removeBtn.textContent = 'Remove from Gallery';
    removeBtn.style.marginTop = '8px';
    removeBtn.addEventListener('click', (e) =>
      this.handleRemoveImageFromGallery(e, card.image?.id, gallery?.id)
    );
    card.appendChild(removeBtn);
    grid.appendChild(card);
    return card;
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
        crop_mode: 'smart_crop'
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
                  <option value="opencv-saliency" ${gallerySettings.crop_mode === 'opencv-saliency' || gallerySettings.crop_mode === 'opencv_saliency' ? 'selected' : ''}>OpenCV Saliency (Smart)</option>
                  <option value="face-portrait" ${(
                    gallerySettings.crop_mode === 'face-portrait' ||
                    gallerySettings.crop_mode === 'face_portrait' ||
                    gallerySettings.crop_mode === 'portrait' ||
                    gallerySettings.crop_mode === 'people' ||
                    gallerySettings.crop_mode === 'face' ||
                    gallerySettings.crop_mode === 'faces'
                  ) ? 'selected' : ''}>Face Portrait (Detect)</option>
                  <option value="fit" ${gallerySettings.crop_mode === 'fit' ? 'selected' : ''}>Fit to Screen</option>
                  <option value="fill" ${gallerySettings.crop_mode === 'fill' ? 'selected' : ''}>Fill Screen</option>
                </select>
              </div>
              <!-- Update interval removed: scheduling handled by external service -->
            </div>
            <div class="settings-section" style="margin-top:32px;">
              <button class="btn btn-danger btn-block" id="delete-gallery-btn" style="margin-top:16px;">🗑️ Delete Gallery</button>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancel-settings">Cancel</button>
            <button class="btn btn-primary" id="save-settings">Save Settings</button>
          </div>
        </div>
      </div>
    `;
    // Add delete gallery handler
    modal.querySelector('#delete-gallery-btn').addEventListener('click', async () => {
      if (!confirm('Are you sure you want to delete this gallery and remove all its images? This cannot be undone.')) return;
      try {
        const res = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels/${gallery.id}`, {
          method: 'DELETE',
          credentials: 'include'
        });
        if (res.ok) {
          // Remove modal and refresh
          if (modal && modal.parentNode === this.shadowRoot) this.shadowRoot.removeChild(modal);
          if (style && style.parentNode === this.shadowRoot) this.shadowRoot.removeChild(style);
          this.state.view = 'gallery-overview';
          this.state.currentGalleryId = null;
          await this.refreshData();
        } else {
          const errorText = await res.text();
          alert('Failed to delete gallery: ' + errorText);
        }
      } catch (error) {
        alert('Error deleting gallery: ' + error.message);
      }
    });

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
        background: var(--modal-backdrop, rgba(0, 0, 0, 0.5));
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .modal-content {
        background: var(--color-surface, #ffffff);
        border-radius: 8px;
        width: 90%;
        max-width: 600px;
        max-height: 90vh;
        overflow-y: auto;
        box-shadow: var(--elevation-2, 0 4px 20px rgba(0, 0, 0, 0.2));
      }
      .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px 24px;
        border-bottom: 1px solid var(--color-border, #D0DDD7);
      }
      .modal-header h2 {
        margin: 0;
        color: var(--color-text, #1A1A1A);
      }
      .close-btn {
        background: none;
        border: none;
        font-size: 24px;
        cursor: pointer;
        color: var(--color-text-tertiary, #64706A);
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .close-btn:hover {
        color: var(--color-text, #1A1A1A);
      }
      .modal-body {
        padding: 24px;
      }
      .settings-section {
        margin-bottom: 32px;
      }
      .settings-section h3 {
        margin: 0 0 16px 0;
        color: var(--color-text-secondary, #3D4A44);
        font-size: 1.1rem;
      }
      .settings-note {
        margin: 0 0 16px 0;
        color: var(--color-text-tertiary, #64706A);
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
        color: var(--color-text-secondary, #3D4A44);
      }
      .form-group input,
      .form-group select,
      .form-group textarea {
        width: 100%;
        padding: 8px 12px;
        border: 1px solid var(--color-border, #D0DDD7);
        background: var(--color-background-alt, #EAF2EE);
        color: var(--color-text, #1A1A1A);
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
        border-top: 1px solid var(--color-border, #D0DDD7);
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
      // Normalize crop mode to canonical values before saving
      let cropMode = modal.querySelector('#crop-mode').value;
      // Normalize aliases to canonical values used by backend
      if (cropMode === 'opencv_saliency') {
        cropMode = 'opencv-saliency';
      }
      if (['face_portrait','portrait','people','face','faces'].includes(cropMode)) {
        cropMode = 'face-portrait';
      }
  // Update interval inputs removed (external scheduler handles cadence)

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
        crop_mode: cropMode
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
          
          this.state.galleries = Array.isArray(galleriesData) ? galleriesData : [];
          
          // For galleries involved in reordering, fetch the detailed content_ids
          if (this.state.galleries.length > 0) {
            const galleryDetailsPromises = this.state.galleries.map(gallery =>
              fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels/${gallery.id}`, { credentials: 'include' })
                .then(res => res.ok ? res.json() : null)
                .catch(() => null)
            );
            
            const galleryDetails = await Promise.all(galleryDetailsPromises);
            
            // Merge the detailed data back into galleries
            this.state.galleries = this.state.galleries.map((gallery, index) => {
              const details = galleryDetails[index];
              if (details) {
                return {
                  ...gallery,
                  contentIds: details.content_ids || [],
                  coverImageId: details.cover_image_id || null
                };
              }
              return {
                ...gallery,
                contentIds: [],
                coverImageId: null
              };
            });
          }
          
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
