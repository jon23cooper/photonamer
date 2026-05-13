# PhotoNamer

A macOS desktop app for photographers to review image metadata, assign GPS locations, and rename and organise photo files.

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![PySide6](https://img.shields.io/badge/PySide6-6.6%2B-green) ![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)

---

## Features

- **Open** DNG, JPEG, and TIFF images via the file menu or by dragging onto the window
- **View** a full-resolution preview with zoom (scroll wheel) and pan (click and drag)
- **Inspect and edit** EXIF metadata — capture date, time, and GPS coordinates
- **Interactive map** — search for a location by name or click anywhere on the map to set the GPS pin; coordinates sync with the metadata fields and vice versa
- **Build a filename** from a base name you choose plus the capture date and time, e.g. `european_shag_2024-04-23_06-15-51.dng`
- **Write** edited metadata back into the image file using ExifTool
- **Rename and move** the file to any folder in one step

---

## Requirements

| Dependency | Purpose |
|---|---|
| macOS | Tested on macOS 13+ |
| Python 3.10+ | Runtime |
| [ExifTool](https://exiftool.org) | Reading and writing image metadata |
| PySide6 | GUI framework (Qt6 for Python) |
| Pillow | JPEG and TIFF image loading |
| rawpy | DNG/RAW image loading |
| requests | Location search via Nominatim/OpenStreetMap |

---

## Installation

### 1. Install ExifTool

ExifTool is required for reading and writing EXIF metadata and must be installed separately via [Homebrew](https://brew.sh):

```bash
brew install exiftool
```

### 2. Clone the repository

```bash
git clone https://github.com/jon23cooper/photonamer.git
cd photonamer
```

### 3. Run the setup script

The setup script creates a Python virtual environment and installs all dependencies:

```bash
bash setup.sh
```

---

## Running the app

```bash
.venv/bin/python main.py
```

To make launching easier, add an alias to your shell profile (`~/.zshrc` or `~/.bash_profile`):

```bash
alias photonamer='cd /path/to/photonamer && .venv/bin/python main.py'
```

---

## Usage

1. **Open a file** — use *File → Open* (`⌘O`) or drag a `.dng`, `.jpg`, or `.tiff` file onto the window
2. **Review the image** — scroll to zoom, click and drag to pan
3. **Check the metadata** — capture date, time, and GPS coordinates are read automatically from the file's EXIF data
4. **Edit if needed** — change the date or time directly in the fields; update the GPS location by searching on the map or clicking anywhere on it
5. **Enter a base name** — type a descriptive name in the *Base name* field; the *Preview* line shows the exact filename that will be created
6. **Save** — click *Save Metadata & Move File…*, choose a destination folder, and the app will:
   - Write any edited metadata back into the image file
   - Rename the file using the pattern `{base_name}_{YYYY-MM-DD}_{HH-MM-SS}.{ext}`
   - Move it to the chosen folder

---

## Supported file formats

| Format | Read | EXIF write |
|---|---|---|
| DNG (RAW) | ✓ embedded preview, fallback to full RAW render | ✓ via ExifTool |
| JPEG | ✓ | ✓ via ExifTool |
| TIFF | ✓ | ✓ via ExifTool |

---

## License

MIT
