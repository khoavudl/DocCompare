"""Unit tests for soffice locator."""

import os
from core.soffice_locator import find_soffice


def test_find_soffice_returns_valid_executable():
    path = find_soffice()
    assert os.path.isfile(path)
    assert os.access(path, os.X_OK)
