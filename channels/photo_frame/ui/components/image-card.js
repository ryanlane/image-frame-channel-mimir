class ImageCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    this.render();
    this.shadowRoot.querySelector('.delete-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      this.dispatchEvent(new CustomEvent('delete-image', {
        bubbles: true,
        composed: true,
        detail: { imageId: this.image.id }
      }));
    });

    this.shadowRoot.querySelector('.cover-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      this.dispatchEvent(new CustomEvent('set-cover-image', {
        bubbles: true,
        composed: true,
        detail: { imageId: this.image.id }
      }));
    });
  }

  set image(image) {
    this._image = image;
    if (this.isConnected) {
      this.render();
    }
  }

  get image() {
    return this._image;
  }

  set isCover(isCover) {
    this._isCover = isCover;
    if (this.isConnected) {
      this.render();
    }
  }

  get isCover() {
    return this._isCover;
  }

  render() {
    if (!this.image) return;
    const apiBaseUrl = window.mimirServerBaseUrl || window.location.origin;
    const thumbnailUrl = `${apiBaseUrl}/api/channels/com.epaperframe.photoframe/data/thumbs/${this.image.filename}`;

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          position: relative;
        }
        .image-card {
          border-radius: 8px;
          overflow: hidden;
          box-shadow: 0 1px 4px rgba(0,0,0,0.06);
          transition: transform 0.2s, box-shadow 0.2s;
        }
        .image-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .image-thumbnail {
          width: 100%;
          height: 150px;
          background-color: #e9ecef;
        }
        .image-thumbnail img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
        .image-info {
          padding: 8px;
          background: white;
        }
        .image-filename {
          font-size: 0.8rem;
          color: #495057;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .image-actions {
          position: absolute;
          top: 8px;
          right: 8px;
          display: flex;
          gap: 4px;
          opacity: 0;
          transition: opacity 0.2s;
        }
        .image-card:hover .image-actions {
          opacity: 1;
        }
        .action-btn {
          background: rgba(0,0,0,0.6);
          color: white;
          border: none;
          border-radius: 50%;
          width: 28px;
          height: 28px;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          font-size: 16px;
        }
        .action-btn:hover {
          background: rgba(0,0,0,0.8);
        }
        .cover-indicator {
          position: absolute;
          top: 8px;
          left: 8px;
          background: #007bff;
          color: white;
          padding: 2px 8px;
          border-radius: 12px;
          font-size: 0.7rem;
          font-weight: 600;
        }
      </style>
      <div class="image-card">
        <div class="image-thumbnail">
          <img src="${thumbnailUrl}" alt="${this.image.filename}" />
        </div>
        <div class="image-info">
          <div class="image-filename">${this.escapeHtml(this.image.filename)}</div>
        </div>
        <div class="image-actions">
          <button class="action-btn cover-btn" title="Set as gallery cover">⭐</button>
          <button class="action-btn delete-btn" title="Delete image">🗑️</button>
        </div>
        ${this.isCover ? `<div class="cover-indicator">Cover</div>` : ''}
      </div>
    `;
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

customElements.define('image-card', ImageCard);
export default ImageCard;
