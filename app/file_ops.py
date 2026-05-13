import re
import shutil
from pathlib import Path


def build_filename(base_name: str, datetime_str: str | None, original_suffix: str) -> str:
    """
    Construct a filename from base_name + date + time + original extension.
    datetime_str format: "YYYY:MM:DD HH:MM:SS"
    """
    safe_base = re.sub(r"[^\w\s-]", "", base_name).strip()
    safe_base = re.sub(r"\s+", "_", safe_base)

    if not safe_base:
        safe_base = "photo"

    parts = [safe_base]

    if datetime_str:
        try:
            date_part, time_part = datetime_str.split(" ", 1)
            parts.append(date_part.replace(":", "-"))
            parts.append(time_part.replace(":", "-"))
        except ValueError:
            pass

    return "_".join(parts) + original_suffix.lower()


def save_and_move(src_path: str | Path, dest_dir: str | Path, new_filename: str) -> Path:
    """Move src_path to dest_dir/new_filename; resolves name collisions."""
    src = Path(src_path)
    dest = Path(dest_dir) / new_filename

    if dest.resolve() == src.resolve():
        return dest

    if dest.exists():
        stem = Path(new_filename).stem
        suffix = Path(new_filename).suffix
        counter = 1
        while dest.exists():
            dest = Path(dest_dir) / f"{stem}_{counter}{suffix}"
            counter += 1

    shutil.move(str(src), str(dest))
    return dest
