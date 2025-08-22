// x-photo-frame-manager Web Component
class XPhotoFrameManager extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.images = [];
  }
  async connectedCallback() {
    await this.loadImages();
    this.render();
  }
  async loadImages() {
    const res = await fetch('/api/channels/com.epaperframe.photoframe/images');
    this.images = await res.json();
  }
  render() {
    this.shadowRoot.innerHTML = `
      <style>@import url('./styles.css');</style>
      <div class="manager-container">
        <h1>Photo Frame Management</h1>
        <div class="image-grid">
          ${this.images.map(img => `
            <div class="image-card" data-id="${img.id}">
              <img src="/channels/photo_frame/data/thumbs/${img.filename}" alt="${img.title || img.original_name}" />
              <div class="image-info">
                <h3>${img.title || img.original_name}</h3>
                <p>${img.description || ''}</p>
                <span>${img.width}×${img.height}</span>
                <span>Shown: ${img.times_shown} times</span>
                <button onclick="deleteImage(${img.id})">🗑️ Delete</button>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }
}
customElements.define('x-photo-frame-manager', XPhotoFrameManager);
