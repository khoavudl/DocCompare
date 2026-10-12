"""Locates the LibreOffice soffice executable on various operating systems."""

import os
import shutil
from pathlib import Path
from core.errors import LibreOfficeNotFoundError


def find_soffice() -> str:
    """Find soffice executable path according to the resolution order in spec:
    1. DOC_COMPARE_SOFFICE environment variable
    2. shutil.which("soffice")
    3. Windows default paths
    4. macOS default application path
    """
    # 1. Environment variable
    env_path = os.environ.get("DOC_COMPARE_SOFFICE")
    if env_path and os.path.isfile(env_path) and os.access(env_path, os.X_OK):
        return env_path

    # 2. PATH resolution
    which_path = shutil.which("soffice")
    if which_path:
        return which_path

    # 3. Windows standard locations
    windows_candidates = [
        Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
        Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
    ]
    for candidate in windows_candidates:
        if candidate.is_file():
            return str(candidate)

    # 4. macOS standard location
    mac_candidate = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    if mac_candidate.is_file() and os.access(mac_candidate, os.X_OK):
        return str(mac_candidate)

    # Not found
    raise LibreOfficeNotFoundError()
