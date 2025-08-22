// x-photo-frame-card Web Component
class XPhotoFrameCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }
  connectedCallback() {
    const user = JSON.parse(this.getAttribute('user') || '{}');
    const settings = JSON.parse(this.getAttribute('settings') || '{}');
    const stats = JSON.parse(this.getAttribute('stats') || '{}');
    this.shadowRoot.innerHTML = `
      <style>@import url('./styles.css');</style>
      <div class="photo-frame-card">
        <img src="/api/channels/com.epaperframe.photoframe/image" alt="Current Photo" class="photo-frame-image" />
        <div class="photo-frame-info">
          <h2>Photo Frame</h2>
          <p>User: ${user.name || 'Unknown'}</p>
          <p>Images: ${stats.image_count || 0}</p>
          <p>Last Update: ${stats.last_update || '-'}</p>
        </div>
      </div>
    `;
  }
}
customElements.define('x-photo-frame-card', XPhotoFrameCard);
