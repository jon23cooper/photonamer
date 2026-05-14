from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QFileDialog,
    QMessageBox, QSizePolicy, QStatusBar,
)

from .image_viewer import ImageViewer, load_image
from .metadata_panel import MetadataPanel
from .map_panel import MapPanel
from .metadata_handler import read_metadata, write_metadata
from .file_ops import build_filename, save_and_move
from .thumbnail_bar import ThumbnailBar

SUPPORTED_EXTENSIONS = {".dng", ".jpg", ".jpeg", ".tif", ".tiff"}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._current_file: Path | None = None
        self._current_metadata: dict = {}

        self.setWindowTitle("PhotoNamer")
        self.resize(1280, 820)
        self.setAcceptDrops(True)
        self._build_ui()
        self._build_menu()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(6)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter, stretch=1)

        # Left: image viewer + thumbnail strip
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        self.image_viewer = ImageViewer()
        left_layout.addWidget(self.image_viewer, stretch=1)

        self.thumb_bar = ThumbnailBar()
        self.thumb_bar.file_selected.connect(self._load_file)
        left_layout.addWidget(self.thumb_bar)

        splitter.addWidget(left_widget)

        # Right: controls
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        self.metadata_panel = MetadataPanel()
        right_layout.addWidget(self.metadata_panel)

        map_group = QGroupBox("Map — click or search to set GPS location")
        map_layout = QVBoxLayout(map_group)
        map_layout.setContentsMargins(4, 4, 4, 4)
        self.map_panel = MapPanel()
        self.map_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        map_layout.addWidget(self.map_panel)
        right_layout.addWidget(map_group, stretch=1)

        right_layout.addWidget(self._build_naming_panel())

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([640, 640])

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._show_status("Open files to get started  (File → Open or ⌘O, or drag files onto the window)")

        self.map_panel.location_changed.connect(self._on_map_location_changed)
        self.metadata_panel.location_changed.connect(self._on_metadata_location_changed)

    def _build_naming_panel(self) -> QGroupBox:
        group = QGroupBox("File Naming")
        layout = QVBoxLayout(group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Base name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g.  vacation_beach")
        self.name_edit.textChanged.connect(self._update_filename_preview)
        row1.addWidget(self.name_edit, stretch=1)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Preview:"))
        self.filename_preview = QLabel("—")
        self.filename_preview.setStyleSheet("color: #555; font-style: italic;")
        self.filename_preview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        row2.addWidget(self.filename_preview, stretch=1)
        layout.addLayout(row2)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save Metadata & Move File…")
        self.save_btn.setEnabled(False)
        self.save_btn.setFixedHeight(34)
        self.save_btn.clicked.connect(self._on_save_and_move)
        btn_row.addStretch()
        btn_row.addWidget(self.save_btn)
        layout.addLayout(btn_row)

        return group

    def _build_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")

        open_action = QAction("Open…", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_open)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

    # ------------------------------------------------------------------
    # File opening / queue management
    # ------------------------------------------------------------------

    def _on_open(self):
        filepaths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Images",
            str(Path.home() / "Pictures"),
            "Images (*.dng *.jpg *.jpeg *.tif *.tiff);;All Files (*)",
        )
        if filepaths:
            self._enqueue([Path(p) for p in filepaths])

    def _enqueue(self, paths: list[Path]):
        """Add paths to the thumbnail queue; load the first new one if nothing is open."""
        valid = [p for p in paths if p.suffix.lower() in SUPPORTED_EXTENSIONS]
        if not valid:
            return

        first_new = None
        for p in valid:
            if p not in (self.thumb_bar._items or {}):
                if first_new is None:
                    first_new = p

        self.thumb_bar.add_files(valid)

        if self._current_file is None and first_new:
            self._load_file(first_new)

    def _load_file(self, filepath: Path):
        self._show_status(f"Loading {filepath.name}…")
        try:
            pixmap = load_image(filepath)
        except Exception as exc:
            QMessageBox.critical(self, "Image Load Error", str(exc))
            self._show_status("Failed to load image.")
            return

        self.image_viewer.load_pixmap(pixmap)

        try:
            metadata = read_metadata(filepath)
        except FileNotFoundError as exc:
            QMessageBox.warning(
                self,
                "exiftool not found",
                str(exc) + "\n\nInstall exiftool and relaunch PhotoNamer.",
            )
            metadata = {}
        except Exception as exc:
            QMessageBox.warning(self, "Metadata Read Error", str(exc))
            metadata = {}

        self._current_file = filepath
        self._current_metadata = metadata
        self.metadata_panel.set_metadata(metadata)
        self.thumb_bar.set_active(filepath)

        lat = metadata.get("latitude")
        lon = metadata.get("longitude")
        if lat is not None and lon is not None:
            QTimer.singleShot(800, lambda: self.map_panel.set_location(lat, lon))

        self.name_edit.setText(filepath.stem)
        self._update_filename_preview()

        self.save_btn.setEnabled(True)
        self.setWindowTitle(f"PhotoNamer — {filepath.name}")
        self._show_status(f"Opened: {filepath}")

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def _on_map_location_changed(self, lat: float, lon: float):
        self.metadata_panel.set_location(lat, lon)

    def _on_metadata_location_changed(self, lat: float, lon: float):
        self.map_panel.set_location(lat, lon)

    def _update_filename_preview(self):
        if not self._current_file:
            self.filename_preview.setText("—")
            return
        base = self.name_edit.text().strip()
        dt_str = self.metadata_panel.get_datetime_str()
        suffix = self._current_file.suffix
        name = build_filename(base or "photo", dt_str, suffix)
        self.filename_preview.setText(name)

    # ------------------------------------------------------------------
    # Save & Move
    # ------------------------------------------------------------------

    def _on_save_and_move(self):
        if not self._current_file:
            return

        base = self.name_edit.text().strip()
        if not base:
            QMessageBox.warning(self, "Missing Name", "Please enter a base name for the file.")
            self.name_edit.setFocus()
            return

        dt_str = self.metadata_panel.get_datetime_str()
        lat = self.metadata_panel.get_latitude()
        lon = self.metadata_panel.get_longitude()

        dialog = QFileDialog(self, "Choose Destination Folder", str(self._current_file.parent))
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
        dialog.setLabelText(QFileDialog.DialogLabel.Accept, "Move Here")

        # Build sidebar: standard locations + every mounted external volume
        from PySide6.QtCore import QUrl
        sidebar = [
            QUrl.fromLocalFile(str(Path.home())),
            QUrl.fromLocalFile(str(Path.home() / "Desktop")),
            QUrl.fromLocalFile(str(Path.home() / "Documents")),
            QUrl.fromLocalFile(str(Path.home() / "Pictures")),
        ]
        volumes = Path("/Volumes")
        if volumes.exists():
            for vol in sorted(volumes.iterdir()):
                if vol.is_dir():
                    sidebar.append(QUrl.fromLocalFile(str(vol)))
        dialog.setSidebarUrls(sidebar)

        if not dialog.exec():
            return
        selected = dialog.selectedFiles()
        if not selected:
            return
        dest_dir = selected[0]

        try:
            write_metadata(self._current_file, datetime_str=dt_str, latitude=lat, longitude=lon)
        except FileNotFoundError as exc:
            QMessageBox.critical(self, "exiftool not found", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Metadata Write Error", str(exc))
            return

        new_filename = build_filename(base, dt_str, self._current_file.suffix)
        try:
            new_path = save_and_move(self._current_file, dest_dir, new_filename)
        except Exception as exc:
            QMessageBox.critical(self, "File Move Error", str(exc))
            return

        self._show_status(f"Saved: {new_path}")

        # Remove from queue and advance to next
        finished = self._current_file
        next_file = self.thumb_bar.next_file(finished)
        self.thumb_bar.remove_file(finished)
        self._current_file = None

        if next_file:
            self._load_file(next_file)
        else:
            self.image_viewer.clear()
            self.save_btn.setEnabled(False)
            self.name_edit.clear()
            self.filename_preview.setText("—")
            self.setWindowTitle("PhotoNamer")
            self._show_status("Queue complete.")

    # ------------------------------------------------------------------
    # Drag and drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            if any(
                Path(u.toLocalFile()).suffix.lower() in SUPPORTED_EXTENSIONS
                for u in event.mimeData().urls()
            ):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        paths = [
            Path(u.toLocalFile())
            for u in event.mimeData().urls()
            if Path(u.toLocalFile()).suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        if paths:
            self._enqueue(paths)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        # Stop background threads before Qt starts tearing down objects
        self.thumb_bar.shutdown()
        # Navigate away so QtWebEngine can shut its renderer process down cleanly
        # before Python destroys our wrapper objects (prevents abort() on exit)
        from PySide6.QtCore import QUrl
        self.map_panel.setUrl(QUrl("about:blank"))
        super().closeEvent(event)

    def _show_status(self, message: str, timeout_ms: int = 0):
        self.status_bar.showMessage(message, timeout_ms)
