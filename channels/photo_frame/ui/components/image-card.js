class ImageCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.isDragging = false;
  }

  connectedCallback() {
    this.render();
    this.attachEventListeners();
  }

  attachEventListeners() {
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

    // Drag and drop event listeners
    const imageCard = this.shadowRoot.querySelector('.image-card');
    
    imageCard.addEventListener('dragstart', (e) => {
      this.isDragging = true;
      imageCard.classList.add('dragging');
      e.dataTransfer.setData('text/plain', this.image.id.toString());
      e.dataTransfer.effectAllowed = 'move';
      
      this.dispatchEvent(new CustomEvent('drag-start', {
        bubbles: true,
        composed: true,
        detail: { imageId: this.image.id }
      }));
    });

    imageCard.addEventListener('dragend', (e) => {
      this.isDragging = false;
      imageCard.classList.remove('dragging');
      
      this.dispatchEvent(new CustomEvent('drag-end', {
        bubbles: true,
        composed: true,
        detail: { imageId: this.image.id }
      }));
    });

    imageCard.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      if (!this.isDragging) {
        imageCard.classList.add('drag-over');
      }
    });

    imageCard.addEventListener('dragleave', (e) => {
      imageCard.classList.remove('drag-over');
    });

    imageCard.addEventListener('drop', (e) => {
      e.preventDefault();
      imageCard.classList.remove('drag-over');
      
      const draggedImageId = e.dataTransfer.getData('text/plain');
      console.log('Drop event triggered:', { draggedImageId, targetImageId: this.image.id.toString() });
      
      if (draggedImageId && draggedImageId !== this.image.id.toString()) {
        console.log('Dispatching image-reorder event');
        this.dispatchEvent(new CustomEvent('image-reorder', {
          bubbles: true,
          composed: true,
          detail: { 
            draggedImageId: draggedImageId,
            targetImageId: this.image.id.toString()
          }
        }));
      } else {
        console.log('Drop ignored - same image or invalid draggedImageId');
      }
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
    
    // Use new thumbnail format: basename.thumb.jpg
    const baseName = this.image.filename.split('.')[0];
    const thumbnailUrl = `${apiBaseUrl}/api/channels/com.epaperframe.photoframe/assets/uploads/${baseName}.thumb.jpg`;
    const originalUrl = `${apiBaseUrl}/api/channels/com.epaperframe.photoframe/assets/uploads/${this.image.filename}`;

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
          cursor: grab;
          background: white;
        }
        .image-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .image-card.dragging {
          opacity: 0.5;
          transform: rotate(5deg);
          cursor: grabbing;
          z-index: 1000;
        }
        .image-card.drag-over {
          border: 2px dashed #007bff;
          background: #f0f8ff;
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0,123,255,0.3);
        }
        .image-thumbnail {
          width: 100%;
          height: 150px;
          background-color: #e9ecef;
          position: relative;
        }
        .image-thumbnail img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
        .thumbnail-fallback {
          display: none;
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
        .thumbnail-placeholder {
          display: none;
          width: 100%;
          height: 100%;
          background: linear-gradient(135deg, #e9ecef 0%, #f8f9fa 100%);
          align-items: center;
          justify-content: center;
          color: #6c757d;
          font-size: 2rem;
        }
        .image-info {
          padding: 8px;
          background: inherit;
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
        .drag-handle {
          position: absolute;
          bottom: 8px;
          right: 8px;
          color: #6c757d;
          font-size: 14px;
          opacity: 0;
          transition: opacity 0.2s;
          cursor: grab;
          background: rgba(255,255,255,0.9);
          border-radius: 4px;
          padding: 4px;
        }
        .image-card:hover .drag-handle {
          opacity: 1;
        }
      </style>
      <div class="image-card" draggable="true">
        <div class="image-thumbnail">
          <img class="thumbnail-primary" src="${thumbnailUrl}" alt="${this.image.filename}" 
               onerror="this.style.display='none'; this.nextElementSibling.style.display='block';" />
          <img class="thumbnail-fallback" src="${originalUrl}" alt="${this.image.filename}"
               onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" />
          <div class="thumbnail-placeholder">🖼️</div>
        </div>
        <div class="image-info">
          <div class="image-filename">${this.escapeHtml(this.image.filename)}</div>
        </div>
        <div class="image-actions">
          <button class="action-btn cover-btn" title="Set as gallery cover">⭐</button>
          <button class="action-btn delete-btn" title="Delete image">🗑️</button>
        </div>
        <div class="drag-handle" title="Drag to reorder">⋮⋮</div>
        ${this.isCover ? `<div class="cover-indicator">Cover</div>` : ''}
      </div>
    `;
    
    // Re-attach event listeners after render
    if (this.isConnected) {
      this.attachEventListeners();
    }
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

customElements.define('image-card', ImageCard);
export default ImageCard;
