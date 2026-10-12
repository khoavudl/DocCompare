"""Helper for resolving static asset paths in dev and PyInstaller frozen modes."""

import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> Path:
    """Returns absolute path to resource, compatible with PyInstaller --onedir/--onefile bundles."""
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller temporary extraction folder or bundle root
        candidate = Path(sys._MEIPASS) / relative_path
        if candidate.exists():
            return candidate

    # Development mode: relative to project root
    project_root = Path(__file__).resolve().parent.parent
    candidate = project_root / relative_path
    if candidate.exists():
        return candidate

    # Fallback to current working directory
    return Path(relative_path).resolve()
