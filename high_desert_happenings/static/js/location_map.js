/**
 * Location Map Initialization
 *
 * Initializes a Leaflet map for displaying a location marker.
 * Reads configuration from data attributes on the #map element.
 *
 * Requires Leaflet library to be loaded first.
 * @see https://unpkg.com/leaflet@1.9.4/dist/leaflet.js
 */

/**
 * Initialize the location map
 */
function initLocationMap() {
  const mapElement = document.getElementById('map');
  if (!mapElement) return;

  const lat = parseFloat(mapElement.dataset.latitude);
  const lng = parseFloat(mapElement.dataset.longitude);
  const name = mapElement.dataset.name;
  const address = mapElement.dataset.address;

  // Validate coordinates
  if (isNaN(lat) || isNaN(lng)) {
    console.error('Invalid map coordinates');
    return;
  }

  // Initialize the map
  const map = L.map('map').setView([lat, lng], 10);

  // Add OpenStreetMap tile layer
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19
  }).addTo(map);

  // Add marker for the location
  const marker = L.marker([lat, lng]).addTo(map);

  // Add popup with location name and address
  const popupContent = `<b>${name}</b>${address ? '<br />' + address : ''}`;
  marker.bindPopup(popupContent);
}

// Wait for both DOM and Leaflet to be ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initLocationMap);
} else {
  // DOM already loaded
  initLocationMap();
}
