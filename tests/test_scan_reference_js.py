# File: tests/test_scan_reference_js.py
"""Exercise maintained browser functions in Node without a live scanner."""
import shutil
import subprocess
from pathlib import Path

import pytest


def test_scan_request_ownership_and_reference_rendering():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required for JavaScript behavior validation')
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([node, str(root / 'tests' / 'scan_reference_contract.cjs')],
                            cwd=root, text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
