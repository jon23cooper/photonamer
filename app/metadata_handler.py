import re
import subprocess
import json
import shutil
from pathlib import Path

_TZ_RE = re.compile(r"[+-]\d{2}:\d{2}$|Z$")


def _exiftool_path():
    # shutil.which respects PATH (works in development)
    path = shutil.which("exiftool")
    if path:
        return path
    # .app bundles don't inherit the shell's PATH, so check Homebrew locations directly
    for candidate in (
        "/opt/homebrew/bin/exiftool",   # Apple Silicon
        "/usr/local/bin/exiftool",       # Intel
    ):
        if Path(candidate).is_file():
            return candidate
    raise FileNotFoundError(
        "exiftool not found. Install it with: brew install exiftool"
    )


_DATETIME_FIELDS = [
    "DateTimeOriginal",
    "SubSecDateTimeOriginal",
    "CreateDate",
    "DateTimeCreated",
]

_DATE_ONLY_FIELDS = [
    "DateCreated",
    "Date",
]


def _normalise_dt(raw_str: str) -> str:
    """Normalise any date/datetime string to 'YYYY:MM:DD HH:MM:SS'."""
    s = _TZ_RE.sub("", raw_str.strip())
    s = s.replace("T", " ")
    s = re.sub(r"^(\d{4})-(\d{2})-(\d{2})", r"\1:\2:\3", s)
    return s[:19]


def read_metadata(filepath):
    """Return dict with keys: datetime, latitude, longitude (all optional)."""
    et = _exiftool_path()
    all_date_fields = _DATETIME_FIELDS + _DATE_ONLY_FIELDS
    date_args = [f"-{f}" for f in all_date_fields]
    result = subprocess.run(
        [
            et, "-json", "-n",
            *date_args,
            "-Time",
            "-GPSLatitude", "-GPSLongitude",
            "-GPSLatitudeRef", "-GPSLongitudeRef",
            str(filepath),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return {}

    raw = json.loads(result.stdout)
    if not raw:
        return {}
    raw = raw[0]

    out = {}

    # Try combined datetime fields first
    for field in _DATETIME_FIELDS:
        val = raw.get(field)
        if val and isinstance(val, str):
            out["datetime"] = _normalise_dt(val)
            break

    # Fall back to date-only fields + separate Time field (e.g. Pentax cameras)
    if "datetime" not in out:
        for field in _DATE_ONLY_FIELDS:
            val = raw.get(field)
            if val and isinstance(val, str):
                date_part = _normalise_dt(val)[:10]   # "YYYY:MM:DD"
                time_part = raw.get("Time", "00:00:00")
                if isinstance(time_part, str):
                    time_part = time_part[:8]          # "HH:MM:SS"
                out["datetime"] = f"{date_part} {time_part}"
                break

    lat = raw.get("GPSLatitude")
    if lat is not None:
        lat_ref = raw.get("GPSLatitudeRef", "N")
        out["latitude"] = -abs(float(lat)) if lat_ref == "S" else abs(float(lat))

    lon = raw.get("GPSLongitude")
    if lon is not None:
        lon_ref = raw.get("GPSLongitudeRef", "E")
        out["longitude"] = -abs(float(lon)) if lon_ref == "W" else abs(float(lon))

    return out


def write_metadata(filepath, datetime_str=None, latitude=None, longitude=None):
    """Write metadata back into the image file using exiftool."""
    et = _exiftool_path()
    args = [et, "-overwrite_original"]

    if datetime_str:
        args += [
            f"-DateTimeOriginal={datetime_str}",
            f"-CreateDate={datetime_str}",
        ]

    if latitude is not None and longitude is not None:
        lat_ref = "N" if latitude >= 0 else "S"
        lon_ref = "E" if longitude >= 0 else "W"
        args += [
            f"-GPSLatitude={abs(latitude)}",
            f"-GPSLatitudeRef={lat_ref}",
            f"-GPSLongitude={abs(longitude)}",
            f"-GPSLongitudeRef={lon_ref}",
        ]

    args.append(str(filepath))
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"exiftool write error: {result.stderr.strip()}")
