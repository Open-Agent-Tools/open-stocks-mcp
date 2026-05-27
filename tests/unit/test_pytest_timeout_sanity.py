"""Sanity test proving pytest-timeout is installed and enforces deadlines."""

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


@pytest.mark.timeout(30)
def test_timeout_kills_hanging_test(tmp_path: Path) -> None:
    """A deliberately hanging test must be terminated by pytest-timeout."""
    test_file = tmp_path / "test_hang.py"
    test_file.write_text(
        textwrap.dedent("""\
            import time

            def test_hang():
                time.sleep(30)
        """)
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(test_file),
            "--timeout=2",
            "--timeout-method=thread",
            "-q",
            "--override-ini=addopts=",
            "--no-header",
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode != 0
    assert "Timeout" in result.stdout or "Timeout" in result.stderr
