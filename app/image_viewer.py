import io
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QWheelEvent, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QSizePolicy

try:
    import rawpy
    _RAWPY_AVAILABLE = True
except ImportError:
    _RAWPY_AVAILABLE = False

try:
    from PIL import Image as PILImage
    _PILLOW_AVAILABLE = True
except ImportError:
    _PILLOW_AVAILABLE = False


def _pil_to_pixmap(img: "PILImage.Image") -> QPixmap:
    img = img.convert("RGB")
    data = img.tobytes("raw", "RGB")
    qimage = QImage(data, img.width, img.height, img.width * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimage)


def load_image(filepath: str | Path) -> QPixmap:
    filepath = Path(filepath)
    ext = filepath.suffix.lower()

    if ext == ".dng":
        if not _RAWPY_AVAILABLE:
            raise RuntimeError("rawpy is required to open DNG files: pip install rawpy")
        with rawpy.imread(str(filepath)) as raw:
            try:
                thumb = raw.extract_thumb()
                if thumb.format == rawpy.ThumbFormat.JPEG:
                    if _PILLOW_AVAILABLE:
                        img = PILImage.open(io.BytesIO(thumb.data))
                        return _pil_to_pixmap(img)
                    else:
                        pixmap = QPixmap()
                        pixmap.loadFromData(thumb.data)
                        return pixmap
                else:
                    if not _PILLOW_AVAILABLE:
                        raise RuntimeError("Pillow required for non-JPEG DNG thumbnails")
                    img = PILImage.fromarray(thumb.data)
                    return _pil_to_pixmap(img)
            except Exception:
                # No embedded thumbnail — fall back to full RAW demosaicing
                if not _PILLOW_AVAILABLE:
                    raise RuntimeError("Pillow required to render DNG without an embedded thumbnail")
                rgb = raw.postprocess(use_camera_wb=True, output_bps=8)
                img = PILImage.fromarray(rgb)
                return _pil_to_pixmap(img)
    else:
        if _PILLOW_AVAILABLE:
            img = PILImage.open(str(filepath))
            return _pil_to_pixmap(img)
        else:
            pixmap = QPixmap(str(filepath))
            if pixmap.isNull():
                raise RuntimeError(f"Could not load image: {filepath}")
            return pixmap


class ImageViewer(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item = None
        self._zoom = 1.0

        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumWidth(300)
        self.setStyleSheet("background-color: #2b2b2b; border: none;")

    def load_pixmap(self, pixmap: QPixmap):
        self._scene.clear()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self._zoom = 1.0
        self.resetTransform()
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def clear(self):
        self._scene.clear()
        self._pixmap_item = None

    def wheelEvent(self, event: QWheelEvent):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom *= factor
        self._zoom = max(0.05, min(self._zoom, 20.0))
        self.scale(factor, factor)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap_item:
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def dragEnterEvent(self, event: QDragEnterEvent):
        self.window().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        self.window().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent):
        self.window().dropEvent(event)
