from PySide6.QtCore import Qt, Signal, QDate, QTime, QDateTime
from PySide6.QtWidgets import (
    QGroupBox, QFormLayout, QDateEdit, QTimeEdit,
    QDoubleSpinBox, QHBoxLayout, QWidget,
)


class MetadataPanel(QGroupBox):
    location_changed = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__("Metadata", parent)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout()
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
        layout.addRow("Date:", self.date_edit)

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm:ss")
        layout.addRow("Time:", self.time_edit)

        self.lat_spin = QDoubleSpinBox()
        self.lat_spin.setRange(-90.0, 90.0)
        self.lat_spin.setDecimals(6)
        self.lat_spin.setSingleStep(0.0001)
        self.lat_spin.setSpecialValueText("—")
        layout.addRow("Latitude:", self.lat_spin)

        self.lon_spin = QDoubleSpinBox()
        self.lon_spin.setRange(-180.0, 180.0)
        self.lon_spin.setDecimals(6)
        self.lon_spin.setSingleStep(0.0001)
        self.lon_spin.setSpecialValueText("—")
        layout.addRow("Longitude:", self.lon_spin)

        self.lat_spin.valueChanged.connect(self._on_coords_changed)
        self.lon_spin.valueChanged.connect(self._on_coords_changed)

        self.setLayout(layout)

    def _on_coords_changed(self):
        lat = self.lat_spin.value()
        lon = self.lon_spin.value()
        if lat != self.lat_spin.minimum() and lon != self.lon_spin.minimum():
            self.location_changed.emit(lat, lon)

    def set_metadata(self, data: dict):
        dt_str = data.get("datetime")
        if dt_str:
            dt = QDateTime.fromString(dt_str, "yyyy:MM:dd HH:mm:ss")
            if dt.isValid():
                self.date_edit.setDate(dt.date())
                self.time_edit.setTime(dt.time())

        lat = data.get("latitude")
        lon = data.get("longitude")

        self.lat_spin.blockSignals(True)
        self.lon_spin.blockSignals(True)
        if lat is not None:
            self.lat_spin.setValue(float(lat))
        else:
            self.lat_spin.setValue(self.lat_spin.minimum())
        if lon is not None:
            self.lon_spin.setValue(float(lon))
        else:
            self.lon_spin.setValue(self.lon_spin.minimum())
        self.lat_spin.blockSignals(False)
        self.lon_spin.blockSignals(False)

    def set_location(self, lat: float, lon: float):
        self.lat_spin.blockSignals(True)
        self.lon_spin.blockSignals(True)
        self.lat_spin.setValue(lat)
        self.lon_spin.setValue(lon)
        self.lat_spin.blockSignals(False)
        self.lon_spin.blockSignals(False)

    def get_datetime_str(self) -> str:
        d = self.date_edit.date()
        t = self.time_edit.time()
        return f"{d.year()}:{d.month():02d}:{d.day():02d} {t.hour():02d}:{t.minute():02d}:{t.second():02d}"

    def get_latitude(self) -> float | None:
        v = self.lat_spin.value()
        return None if v == self.lat_spin.minimum() else v

    def get_longitude(self) -> float | None:
        v = self.lon_spin.value()
        return None if v == self.lon_spin.minimum() else v
