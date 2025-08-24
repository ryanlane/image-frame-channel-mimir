// x-gallery-manager Web Component for Photo Frame Gallery Management
class XGalleryManager extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.galleries = [];
    this.allImages = [];
    this.currentView = 'galleries'; // 'galleries' or 'gallery-detail'
    this.selectedGallery = null;
    this.apiBaseUrl = this.getApiBaseUrl();
  }

  getApiBaseUrl() {
    return window.mimirServerBaseUrl || window.location.origin;
  }

  async connectedCallback() {
    await this.loadData();
    this.render();
    this.attachEventListeners();
  }

  async loadData() {
    try {
      // Load galleries
      const galleriesRes = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels`, {
        credentials: 'include'
      });
      this.galleries = await galleriesRes.json();

      // Load all images for gallery management
      const imagesRes = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/images`, {
        credentials: 'include'
      });
      this.allImages = await imagesRes.json();

      // Create default gallery if no galleries exist
      if (this.galleries.length === 0) {
        await this.createDefaultGallery();
      }

    } catch (error) {
      console.error('Failed to load gallery data:', error);
      this.galleries = [];
      this.allImages = [];
    }
  }

  async createDefaultGallery() {
    try {
      const defaultGallery = {
        name: "All Photos",
        description: "All photos in your collection",
        tags: []
      };

      const response = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(defaultGallery)
      });

      if (response.ok) {
        const newGallery = await response.json();
        
        // Assign all existing images to the default gallery
        if (this.allImages.length > 0) {
          const imageIds = this.allImages.map(img => img.id.toString());
          await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels/${newGallery.id}/content`, {
            method: 'POST',
            credentials: 'include',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content_ids: imageIds, action: 'set' })
          });
        }

        this.galleries = [newGallery];
      }
    } catch (error) {
      console.error('Failed to create default gallery:', error);
    }
  }

  render() {
    if (this.currentView === 'galleries') {
      this.renderGalleryGrid();
    } else if (this.currentView === 'gallery-detail') {
      this.renderGalleryDetail();
    }
  }

  renderGalleryGrid() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .gallery-manager {
          padding: 24px;
          background: #f8f9fa;
          min-height: 100vh;
        }
        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 32px;
        }
        .header h1 {
          margin: 0;
          color: #212529;
          font-size: 1.75rem;
        }
        .btn-primary {
          background: #007bff;
          color: white;
          border: none;
          border-radius: 6px;
          padding: 12px 24px;
          cursor: pointer;
          font-weight: 500;
          font-size: 0.9rem;
          transition: background 0.2s;
        }
        .btn-primary:hover {
          background: #0056b3;
        }
        .gallery-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
          gap: 24px;
        }
        .gallery-card {
          background: white;
          border-radius: 12px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.08);
          overflow: hidden;
          transition: transform 0.2s, box-shadow 0.2s;
          cursor: pointer;
        }
        .gallery-card:hover {
          transform: translateY(-4px);
          box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        }
        .gallery-cover {
          width: 100%;
          height: 200px;
          background: #f8f9fa;
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
          overflow: hidden;
        }
        .gallery-cover img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
        .gallery-cover .placeholder {
          color: #6c757d;
          font-size: 3rem;
        }
        .gallery-info {
          padding: 20px;
        }
        .gallery-name {
          font-size: 1.25rem;
          font-weight: 600;
          color: #212529;
          margin: 0 0 8px 0;
        }
        .gallery-description {
          color: #6c757d;
          font-size: 0.9rem;
          margin: 0 0 12px 0;
          line-height: 1.4;
        }
        .gallery-stats {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 0.85rem;
          color: #868e96;
        }
        .gallery-count {
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .gallery-tags {
          display: flex;
          gap: 4px;
        }
        .tag {
          background: #e9ecef;
          color: #495057;
          padding: 2px 8px;
          border-radius: 12px;
          font-size: 0.75rem;
        }
        .empty-state {
          text-align: center;
          padding: 60px 20px;
          color: #6c757d;
        }
        .empty-state h3 {
          margin: 0 0 12px 0;
          color: #495057;
        }
        .create-gallery-card {
          background: linear-gradient(135deg, #007bff, #0056b3);
          color: white;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          text-align: center;
          min-height: 280px;
          border: 2px dashed rgba(255,255,255,0.3);
        }
        .create-gallery-card:hover {
          border-color: rgba(255,255,255,0.6);
          background: linear-gradient(135deg, #0056b3, #004085);
        }
        .create-icon {
          font-size: 3rem;
          margin-bottom: 16px;
          opacity: 0.8;
        }
        .create-text {
          font-size: 1.1rem;
          font-weight: 500;
          margin: 0;
        }
        .create-subtext {
          font-size: 0.9rem;
          opacity: 0.8;
          margin: 8px 0 0 0;
        }
      </style>

      <div class="gallery-manager">
        <div class="header">
          <h1>📸 Photo Galleries</h1>
          <button class="btn-primary" onclick="this.getRootNode().host.showCreateGalleryDialog()">
            ➕ New Gallery
          </button>
        </div>

        <div class="gallery-grid">
          ${this.galleries.length === 0 ? `
            <div class="empty-state">
              <h3>No galleries yet</h3>
              <p>Create your first gallery to organize your photos</p>
            </div>
          ` : ''}
          
          ${this.galleries.map(gallery => this.renderGalleryCard(gallery)).join('')}
          
          <div class="gallery-card create-gallery-card" onclick="this.getRootNode().host.showCreateGalleryDialog()">
            <div class="create-icon">➕</div>
            <p class="create-text">Create New Gallery</p>
            <p class="create-subtext">Organize your photos into collections</p>
          </div>
        </div>
      </div>
    `;
  }

  renderGalleryCard(gallery) {
    const coverImageUrl = this.getCoverImageUrl(gallery);
    const imageCount = gallery.imageCount || 0;
    const tags = gallery.tags || [];

    return `
      <div class="gallery-card" onclick="this.getRootNode().host.openGallery('${gallery.id}')">
        <div class="gallery-cover">
          ${coverImageUrl ? 
            `<img src="${coverImageUrl}" alt="${gallery.name}" />` : 
            `<div class="placeholder">🖼️</div>`
          }
        </div>
        <div class="gallery-info">
          <h3 class="gallery-name">${this.escapeHtml(gallery.name)}</h3>
          <p class="gallery-description">${this.escapeHtml(gallery.description || 'No description')}</p>
          <div class="gallery-stats">
            <div class="gallery-count">
              <span>📷</span>
              <span>${imageCount} photo${imageCount !== 1 ? 's' : ''}</span>
            </div>
            <div class="gallery-tags">
              ${tags.slice(0, 2).map(tag => `<span class="tag">${this.escapeHtml(tag)}</span>`).join('')}
              ${tags.length > 2 ? `<span class="tag">+${tags.length - 2}</span>` : ''}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  getCoverImageUrl(gallery) {
    if (gallery.coverImageId) {
      const coverImage = this.allImages.find(img => img.id.toString() === gallery.coverImageId);
      if (coverImage) {
        return `${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/data/thumbs/${coverImage.filename}`;
      }
    }
    
    // If no cover image, try to find the first image in the gallery
    if (gallery.contentIds && gallery.contentIds.length > 0) {
      const firstImage = this.allImages.find(img => img.id.toString() === gallery.contentIds[0]);
      if (firstImage) {
        return `${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/data/thumbs/${firstImage.filename}`;
      }
    }
    
    return null;
  }

  renderGalleryDetail() {
    if (!this.selectedGallery) {
      this.currentView = 'galleries';
      this.render();
      return;
    }

    // Load the existing photo frame manager for this specific gallery
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .gallery-header {
          background: white;
          padding: 20px 24px;
          border-bottom: 1px solid #dee2e6;
          display: flex;
          align-items: center;
          gap: 16px;
        }
        .back-button {
          background: #f8f9fa;
          border: 1px solid #dee2e6;
          border-radius: 6px;
          padding: 8px 12px;
          cursor: pointer;
          font-size: 0.9rem;
          color: #495057;
        }
        .back-button:hover {
          background: #e9ecef;
        }
        .gallery-title {
          flex: 1;
        }
        .gallery-title h1 {
          margin: 0 0 4px 0;
          color: #212529;
          font-size: 1.5rem;
        }
        .gallery-title p {
          margin: 0;
          color: #6c757d;
          font-size: 0.9rem;
        }
        .gallery-actions {
          display: flex;
          gap: 12px;
        }
        .btn-secondary {
          background: #6c757d;
          color: white;
          border: none;
          border-radius: 6px;
          padding: 8px 16px;
          cursor: pointer;
          font-size: 0.85rem;
        }
        .btn-secondary:hover {
          background: #545b62;
        }
        .btn-danger {
          background: #dc3545;
          color: white;
          border: none;
          border-radius: 6px;
          padding: 8px 16px;
          cursor: pointer;
          font-size: 0.85rem;
        }
        .btn-danger:hover {
          background: #c82333;
        }
      </style>

      <div class="gallery-header">
        <button class="back-button" onclick="this.getRootNode().host.goBack()">
          ← Back to Galleries
        </button>
        <div class="gallery-title">
          <h1>${this.escapeHtml(this.selectedGallery.name)}</h1>
          <p>${this.escapeHtml(this.selectedGallery.description || 'No description')}</p>
        </div>
        <div class="gallery-actions">
          <button class="btn-secondary" onclick="this.getRootNode().host.editGallery()">
            ✏️ Edit
          </button>
          <button class="btn-danger" onclick="this.getRootNode().host.deleteGallery()" 
                  ${this.selectedGallery.id === 'all_photos' ? 'disabled' : ''}>
            🗑️ Delete
          </button>
        </div>
      </div>

      <x-photo-frame-manager gallery-id="${this.selectedGallery.id}"></x-photo-frame-manager>
    `;

    // Load the photo frame manager component for this gallery
    if (!customElements.get('x-photo-frame-manager')) {
      import('./manage.esm.js');
    }
  }

  attachEventListeners() {
    // Event listeners are handled through onclick attributes in the HTML
  }

  // Public methods
  async openGallery(galleryId) {
    this.selectedGallery = this.galleries.find(g => g.id === galleryId);
    if (this.selectedGallery) {
      this.currentView = 'gallery-detail';
      this.render();
    }
  }

  goBack() {
    this.currentView = 'galleries';
    this.selectedGallery = null;
    this.render();
  }

  async showCreateGalleryDialog() {
    const name = prompt('Gallery name:');
    if (!name) return;

    const description = prompt('Gallery description (optional):') || '';

    try {
      const response = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name, description })
      });

      if (response.ok) {
        await this.loadData();
        this.render();
      } else {
        alert('Failed to create gallery');
      }
    } catch (error) {
      console.error('Error creating gallery:', error);
      alert('Failed to create gallery');
    }
  }

  async editGallery() {
    if (!this.selectedGallery) return;

    const newName = prompt('Gallery name:', this.selectedGallery.name);
    if (!newName) return;

    const newDescription = prompt('Gallery description:', this.selectedGallery.description || '') || '';

    try {
      const response = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels/${this.selectedGallery.id}`, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name: newName, description: newDescription })
      });

      if (response.ok) {
        this.selectedGallery.name = newName;
        this.selectedGallery.description = newDescription;
        await this.loadData();
        this.render();
      } else {
        alert('Failed to update gallery');
      }
    } catch (error) {
      console.error('Error updating gallery:', error);
      alert('Failed to update gallery');
    }
  }

  async deleteGallery() {
    if (!this.selectedGallery || this.selectedGallery.id === 'all_photos') return;

    if (!confirm(`Are you sure you want to delete "${this.selectedGallery.name}"? This won't delete the photos, just the gallery organization.`)) {
      return;
    }

    try {
      const response = await fetch(`${this.apiBaseUrl}/api/channels/com.epaperframe.photoframe/subchannels/${this.selectedGallery.id}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (response.ok) {
        await this.loadData();
        this.goBack();
      } else {
        alert('Failed to delete gallery');
      }
    } catch (error) {
      console.error('Error deleting gallery:', error);
      alert('Failed to delete gallery');
    }
  }

  async refreshData() {
    await this.loadData();
    this.render();
  }

  // Utility methods
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// Register the custom element
customElements.define('x-gallery-manager', XGalleryManager);

export default XGalleryManager;
