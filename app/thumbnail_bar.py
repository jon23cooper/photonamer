from pathlib import Path

from PySide6.QtCore import Qt, Signal, QObject, QThread, Slot
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QWidget, QScrollArea, QHBoxLayout, QVBoxLayout,
    QLabel, QFrame, QSizePolicy,
)

THUMB_W = 110
THUMB_H = 82

_STYLE_IDLE   = "background:#3a3a3a; border:2px solid transparent; border-radius:4px;"
_STYLE_ACTIVE = "background:#3a3a3a; border:2px solid #0078d4;     border-radius:4px;"


class ThumbnailItem(QFrame):
    clicked = Signal(Path)

    def __init__(self, filepath: Path, parent=None):
        super().__init__(parent)
        self._path = filepath
        self.setFixedSize(THUMB_W + 10, THUMB_H + 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(_STYLE_IDLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self._img_label = QLabel()
        self._img_label.setFixedSize(THUMB_W, THUMB_H)
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_label.setStyleSheet("background:#222; border:none;")
        layout.addWidget(self._img_label)

        name_label = QLabel()
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("color:#bbb; font-size:10px; border:none; background:transparent;")
        name_label.setFixedWidth(THUMB_W)
        elided = name_label.fontMetrics().elidedText(
            filepath.name, Qt.TextElideMode.ElideMiddle, THUMB_W
        )
        name_label.setText(elided)
        layout.addWidget(name_label)

    def set_pixmap(self, pixmap: QPixmap):
        scaled = pixmap.scaled(
            THUMB_W, THUMB_H,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._img_label.setPixmap(scaled)

    def set_active(self, active: bool):
        self.setStyleSheet(_STYLE_ACTIVE if active else _STYLE_IDLE)

    def mousePressEvent(self, event):
        self.clicked.emit(self._path)


# ---------------------------------------------------------------------------
# Background thumbnail loader
# ---------------------------------------------------------------------------

class _ThumbWorker(QObject):
    """Loads thumbnails in a worker thread; emits QImage data (not QPixmap)."""
    ready = Signal(Path, int, int, bytes)   # path, w, h, RGB bytes
    finished = Signal()

    def __init__(self, paths: list[Path]):
        super().__init__()
        self._paths = paths

    @Slot()
    def run(self):
        for path in self._paths:
            try:
                w, h, data = _load_thumb_rgb(path)
                self.ready.emit(path, w, h, data)
            except Exception:
                self.ready.emit(path, 0, 0, b"")
        self.finished.emit()


def _load_thumb_rgb(filepath: Path, max_w=THUMB_W, max_h=THUMB_H) -> tuple[int, int, bytes]:
    """Return (width, height, raw-RGB-bytes) suitable for QImage. Thread-safe."""
    import io
    ext = filepath.suffix.lower()

    try:
        from PIL import Image as PILImage
    except ImportError:
        raise RuntimeError("Pillow required for thumbnails")

    img = None

    if ext == ".dng":
        try:
            import rawpy
            with rawpy.imread(str(filepath)) as raw:
                try:
                    thumb = raw.extract_thumb()
                    if thumb.format == rawpy.ThumbFormat.JPEG:
                        img = PILImage.open(io.BytesIO(thumb.data))
                    else:
                        img = PILImage.fromarray(thumb.data)
                except Exception:
                    rgb = raw.postprocess(use_camera_wb=True, output_bps=8, half_size=True)
                    img = PILImage.fromarray(rgb)
        except Exception:
            pass

    if img is None:
        img = PILImage.open(str(filepath))

    img = img.convert("RGB")
    img.thumbnail((max_w, max_h), PILImage.LANCZOS)
    w, h = img.size
    return w, h, img.tobytes("raw", "RGB")


# ---------------------------------------------------------------------------
# Thumbnail bar
# ---------------------------------------------------------------------------

class ThumbnailBar(QWidget):
    file_selected = Signal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(THUMB_H + 52)
        self.setStyleSheet("background:#2b2b2b;")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("background:#2b2b2b;")

        self._container = QWidget()
        self._container.setStyleSheet("background:#2b2b2b;")
        self._row = QHBoxLayout(self._container)
        self._row.setContentsMargins(6, 4, 6, 4)
        self._row.setSpacing(6)
        self._row.addStretch()

        self._scroll.setWidget(self._container)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._scroll)

        self._items: dict[Path, ThumbnailItem] = {}
        self._active: Path | None = None
        self._thread: QThread | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_files(self, paths: list[Path]):
        """Add files to the bar and start background thumbnail loading."""
        new_paths = [p for p in paths if p not in self._items]
        if not new_paths:
            return

        for path in new_paths:
            item = ThumbnailItem(path)
            item.clicked.connect(self.file_selected)
            self._row.insertWidget(self._row.count() - 1, item)
            self._items[path] = item

        self._start_loader(new_paths)

    def remove_file(self, filepath: Path):
        item = self._items.pop(filepath, None)
        if item:
            self._row.removeWidget(item)
            item.deleteLater()
        if self._active == filepath:
            self._active = None

    def set_active(self, filepath: Path):
        if self._active and self._active in self._items:
            self._items[self._active].set_active(False)
        self._active = filepath
        if filepath in self._items:
            self._items[filepath].set_active(True)
            self._scroll_to(self._items[filepath])

    def next_file(self, after: Path) -> Path | None:
        keys = list(self._items.keys())
        try:
            idx = keys.index(after)
            return keys[idx + 1] if idx + 1 < len(keys) else (keys[idx - 1] if idx > 0 else None)
        except ValueError:
            return keys[0] if keys else None

    def is_empty(self) -> bool:
        return not self._items

    def clear(self):
        for item in self._items.values():
            self._row.removeWidget(item)
            item.deleteLater()
        self._items.clear()
        self._active = None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _start_loader(self, paths: list[Path]):
        worker = _ThumbWorker(paths)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.ready.connect(self._on_thumb_ready)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()
        # Keep reference so thread isn't GC'd mid-run
        self._thread = thread

    @Slot(Path, int, int, bytes)
    def _on_thumb_ready(self, path: Path, w: int, h: int, data: bytes):
        item = self._items.get(path)
        if not item:
            return
        if w > 0 and h > 0 and data:
            qimage = QImage(data, w, h, w * 3, QImage.Format.Format_RGB888)
            item.set_pixmap(QPixmap.fromImage(qimage))

    def _scroll_to(self, item: ThumbnailItem):
        self._scroll.ensureWidgetVisible(item)
