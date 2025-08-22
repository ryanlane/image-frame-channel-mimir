// x-photo-frame-card Web Component for Mimir Platform v2.4
class XPhotoFrameCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    this.render();
    
    // Listen for host prop updates
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'attributes' && mutation.attributeName === 'data-hostprops') {
          this.render();
        }
      });
    });
    observer.observe(this, { attributes: true });
  }

  render() {
    const hostProps = JSON.parse(this.getAttribute('data-hostprops') || '{}');
    const user = hostProps.user || {};
    const settings = hostProps.settings || {};
    const stats = hostProps.stats || {};

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .photo-frame-card {
          border: 1px solid #e1e5e9;
          border-radius: 8px;
          padding: 16px;
          background: #ffffff;
          box-shadow: 0 2px 8px rgba(0,0,0,0.05);
          max-width: 400px;
        }
        .photo-frame-image {
          width: 100%;
          height: 200px;
          object-fit: cover;
          border-radius: 6px;
          margin-bottom: 12px;
          background: #f8f9fa;
        }
        .photo-frame-info {
          font-size: 0.9rem;
          color: #495057;
        }
        .photo-frame-info h2 {
          margin: 0 0 8px 0;
          font-size: 1.1rem;
          color: #212529;
        }
        .photo-frame-info p {
          margin: 4px 0;
        }
        .stats-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
          margin-top: 8px;
        }
        .stat-item {
          background: #f8f9fa;
          padding: 8px;
          border-radius: 4px;
          text-align: center;
          font-size: 0.8rem;
        }
        .refresh-button {
          background: #007bff;
          color: white;
          border: none;
          border-radius: 4px;
          padding: 8px 16px;
          cursor: pointer;
          margin-top: 12px;
          font-size: 0.9rem;
        }
        .refresh-button:hover {
          background: #0056b3;
        }
      </style>
      <div class="photo-frame-card">
        <img 
          src="/api/channels/com.epaperframe.photoframe/image?t=${Date.now()}" 
          alt="Current Photo" 
          class="photo-frame-image"
          onerror="this.style.display='none'"
        />
        <div class="photo-frame-info">
          <h2>Photo Frame</h2>
          <div class="stats-grid">
            <div class="stat-item">
              <strong>${stats.image_count || 0}</strong><br>
              Images
            </div>
            <div class="stat-item">
              <strong>${stats.enabled_images || 0}</strong><br>
              Enabled
            </div>
          </div>
          <p><strong>Last Update:</strong> ${stats.last_update ? new Date(stats.last_update).toLocaleString() : 'Never'}</p>
          <button class="refresh-button" onclick="this.parentElement.parentElement.parentElement.host.refreshImage()">
            Refresh Image
          </button>
        </div>
      </div>
    `;
  }

  async refreshImage() {
    try {
      const response = await fetch('/api/channels/com.epaperframe.photoframe/test', {
        method: 'POST',
        credentials: 'include'
      });
      
      if (response.ok) {
        // Refresh the image by updating the src with a new timestamp
        const img = this.shadowRoot.querySelector('.photo-frame-image');
        if (img) {
          img.src = `/api/channels/com.epaperframe.photoframe/image?t=${Date.now()}`;
        }
        
        // Emit event to notify host of update
        this.dispatchEvent(new CustomEvent('photo-frame-updated', {
          bubbles: true,
          detail: { timestamp: Date.now() }
        }));
      }
    } catch (error) {
      console.error('Failed to refresh image:', error);
    }
  }
}

customElements.define('x-photo-frame-card', XPhotoFrameCard);
