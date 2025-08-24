class GalleryCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    this.render();
    this.addEventListener('click', () => {
      this.dispatchEvent(new CustomEvent('gallery-selected', {
        bubbles: true,
        composed: true,
        detail: { galleryId: this.gallery.id }
      }));
    });
  }

  set gallery(gallery) {
    this._gallery = gallery;
    if (this.isConnected) {
      this.render();
    }
  }

  get gallery() {
    return this._gallery;
  }

  set allImages(images) {
    this._allImages = images;
  }

  get allImages() {
    return this._allImages || [];
  }

  render() {
    if (!this.gallery) return;

    const coverImageUrl = this.getCoverImageUrl(this.gallery);
    const imageCount = this.gallery.imageCount || 0;
    const tags = this.gallery.tags || [];

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          cursor: pointer;
        }
        .gallery-card {
          background: white;
          border-radius: 12px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.08);
          overflow: hidden;
          transition: transform 0.2s, box-shadow 0.2s;
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
      </style>
      <div class="gallery-card">
        <div class="gallery-cover">
          ${coverImageUrl ? 
            `<img src="${coverImageUrl}" alt="${this.gallery.name}" />` : 
            `<div class="placeholder">🖼️</div>`
          }
        </div>
        <div class="gallery-info">
          <h3 class="gallery-name">${this.escapeHtml(this.gallery.name)}</h3>
          <p class="gallery-description">${this.escapeHtml(this.gallery.description || 'No description')}</p>
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
    const apiBaseUrl = window.mimirServerBaseUrl || window.location.origin;
    if (gallery.coverImageId) {
      const coverImage = this.allImages.find(img => img.id.toString() === gallery.coverImageId);
      if (coverImage) {
        return `${apiBaseUrl}/api/channels/com.epaperframe.photoframe/assets/uploads/${coverImage.filename.replace(/\.[^/.]+$/, '')}.thumb.jpg`;
      }
    }
    
    if (gallery.contentIds && gallery.contentIds.length > 0) {
      const firstImage = this.allImages.find(img => img.id.toString() === gallery.contentIds[0]);
      if (firstImage) {
        return `${apiBaseUrl}/api/channels/com.epaperframe.photoframe/assets/uploads/${firstImage.filename.replace(/\.[^/.]+$/, '')}.thumb.jpg`;
      }
    }
    
    return null;
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

customElements.define('gallery-card', GalleryCard);
export default GalleryCard;
