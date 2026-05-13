from PySide6.QtCore import QObject, Signal, Slot, QEvent
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

MAP_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, sans-serif; }
  #search-box {
    position: absolute; top: 10px; left: 50px; z-index: 1000;
    display: flex; gap: 4px;
    background: white; padding: 6px 8px; border-radius: 6px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
  }
  #search-input {
    width: 240px; padding: 5px 8px;
    border: 1px solid #ccc; border-radius: 4px;
    font-size: 13px; outline: none;
  }
  #search-input:focus { border-color: #0078d4; }
  #search-btn {
    padding: 5px 12px; background: #0078d4; color: white;
    border: none; border-radius: 4px; cursor: pointer; font-size: 13px;
  }
  #search-btn:hover { background: #006cbf; }
  #map { width: 100%; height: 100vh; }
  #coords {
    position: absolute; bottom: 24px; left: 10px; z-index: 1000;
    background: rgba(255,255,255,0.88); padding: 4px 8px;
    border-radius: 4px; font-size: 12px; color: #333;
    box-shadow: 0 1px 4px rgba(0,0,0,0.2);
  }
</style>
</head>
<body>
<div id="search-box">
  <input id="search-input" type="text" placeholder="Search for a location…"/>
  <button id="search-btn">Search</button>
</div>
<div id="map"></div>
<div id="coords">Click the map to set GPS location</div>
<script>
var map = L.map('map').setView([20, 0], 2);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  maxZoom: 19
}).addTo(map);

var marker = null;
var bridge = null;

new QWebChannel(qt.webChannelTransport, function(channel) {
  bridge = channel.objects.bridge;
});

function setMarker(lat, lng) {
  if (marker) { map.removeLayer(marker); }
  marker = L.marker([lat, lng]).addTo(map);
  document.getElementById('coords').textContent =
    'Lat: ' + lat.toFixed(6) + '  Lon: ' + lng.toFixed(6);
  if (bridge) { bridge.locationSelected(lat, lng); }
}

map.on('click', function(e) {
  setMarker(e.latlng.lat, e.latlng.lng);
});

function doSearch() {
  var query = document.getElementById('search-input').value.trim();
  if (!query) return;
  fetch(
    'https://nominatim.openstreetmap.org/search?format=json&limit=1&q=' +
    encodeURIComponent(query),
    { headers: { 'Accept-Language': 'en-US,en' } }
  )
  .then(function(r) { return r.json(); })
  .then(function(data) {
    if (data && data.length > 0) {
      var lat = parseFloat(data[0].lat);
      var lng = parseFloat(data[0].lon);
      map.setView([lat, lng], 13);
      setMarker(lat, lng);
    } else {
      document.getElementById('coords').textContent = 'Location not found';
    }
  })
  .catch(function(e) {
    document.getElementById('coords').textContent = 'Search error — check network';
  });
}

document.getElementById('search-btn').onclick = doSearch;
document.getElementById('search-input').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') doSearch();
});

function setLocation(lat, lng) {
  map.setView([lat, lng], 13);
  setMarker(lat, lng);
}
</script>
</body>
</html>
"""


class _Bridge(QObject):
    location_selected = Signal(float, float)

    @Slot(float, float)
    def locationSelected(self, lat: float, lng: float):
        self.location_selected.emit(lat, lng)


class MapPanel(QWebEngineView):
    location_changed = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bridge = _Bridge()
        self._bridge.location_selected.connect(self.location_changed)

        self._channel = QWebChannel(self.page())
        self._channel.registerObject("bridge", self._bridge)
        self.page().setWebChannel(self._channel)

        self.setHtml(MAP_HTML)
        self.setMinimumHeight(280)
        self.setAcceptDrops(True)

        # QWebEngineView renders via an internal child widget — install the
        # event filter there too so file drops work over the map surface.
        for child in self.findChildren(QObject):
            if hasattr(child, "setAcceptDrops"):
                child.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.DragEnter:
            self.window().dragEnterEvent(event)
            return event.isAccepted()
        if event.type() == QEvent.Type.DragMove:
            self.window().dragEnterEvent(event)
            return event.isAccepted()
        if event.type() == QEvent.Type.Drop:
            self.window().dropEvent(event)
            return event.isAccepted()
        return super().eventFilter(obj, event)

    def dragEnterEvent(self, event: QDragEnterEvent):
        self.window().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        self.window().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent):
        self.window().dropEvent(event)

    def set_location(self, lat: float, lon: float):
        self.page().runJavaScript(f"setLocation({lat}, {lon});")
