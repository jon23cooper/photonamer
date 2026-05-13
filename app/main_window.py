from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
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

SUPPORTED_EXTENSIONS = {".dng", ".jpg", ".jpeg", ".tif", ".tiff"}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._current_file: Path | None = None
        self._current_metadata: dict = {}

        self.setWindowTitle("PhotoNamer")
        self.resize(1280, 780)
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

        # Left: image viewer
        self.image_viewer = ImageViewer()
        splitter.addWidget(self.image_viewer)

        # Right: controls
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        # Metadata panel
        self.metadata_panel = MetadataPanel()
        right_layout.addWidget(self.metadata_panel)

        # Map panel (inside a GroupBox)
        map_group = QGroupBox("Map — click or search to set GPS location")
        map_layout = QVBoxLayout(map_group)
        map_layout.setContentsMargins(4, 4, 4, 4)
        self.map_panel = MapPanel()
        self.map_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        map_layout.addWidget(self.map_panel)
        right_layout.addWidget(map_group, stretch=1)

        # File naming panel
        right_layout.addWidget(self._build_naming_panel())

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([640, 640])

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._show_status("Open a file to get started  (File → Open or ⌘O)")

        # Wire signals
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
    # File opening
    # ------------------------------------------------------------------

    def _on_open(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            str(Path.home() / "Pictures"),
            "Images (*.dng *.jpg *.jpeg *.tif *.tiff);;All Files (*)",
        )
        if filepath:
            self._load_file(Path(filepath))

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

        lat = metadata.get("latitude")
        lon = metadata.get("longitude")
        if lat is not None and lon is not None:
            QTimer.singleShot(800, lambda: self.map_panel.set_location(lat, lon))

        # Populate base name from existing filename (minus extension)
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

        # Choose destination folder
        dest_dir = QFileDialog.getExistingDirectory(
            self,
            "Choose Destination Folder",
            str(self._current_file.parent),
        )
        if not dest_dir:
            return

        # Write metadata
        try:
            write_metadata(
                self._current_file,
                datetime_str=dt_str,
                latitude=lat,
                longitude=lon,
            )
        except FileNotFoundError as exc:
            QMessageBox.critical(self, "exiftool not found", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Metadata Write Error", str(exc))
            return

        # Build filename and move
        new_filename = build_filename(base, dt_str, self._current_file.suffix)
        try:
            new_path = save_and_move(self._current_file, dest_dir, new_filename)
        except Exception as exc:
            QMessageBox.critical(self, "File Move Error", str(exc))
            return

        self._current_file = new_path
        self.setWindowTitle(f"PhotoNamer — {new_path.name}")
        self._show_status(f"Saved: {new_path}")
        QMessageBox.information(
            self,
            "Done",
            f"File saved as:\n{new_path}",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(
                Path(u.toLocalFile()).suffix.lower() in SUPPORTED_EXTENSIONS
                for u in urls
            ):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            filepath = Path(url.toLocalFile())
            if filepath.suffix.lower() in SUPPORTED_EXTENSIONS:
                self._load_file(filepath)
                break  # open first valid file only

    def _show_status(self, message: str, timeout_ms: int = 0):
        self.status_bar.showMessage(message, timeout_ms)
