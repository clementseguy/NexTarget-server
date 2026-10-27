"""The staging lock must execute only its own launcher."""

import os
from pathlib import Path
import subprocess
import sys


LOCK_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "staging_lock.py"


def _environment(tmp_path: Path) -> dict[str, str]:
    return {
        **os.environ,
        "TMPDIR": str(tmp_path),
        "NEXTARGET_STAGING_LOCK_ARGC": "1",
        "NEXTARGET_STAGING_LOCK_ARG1": "--help",
        "NEXTARGET_STAGING_LOCK_ARG2": "",
        "NEXTARGET_STAGING_LOCK_ARG3": "",
    }


def test_lock_ignores_supplied_paths_and_commands(tmp_path: Path) -> None:
    marker = tmp_path / "unexpected-execution"
    other_script = tmp_path / "other.sh"
    other_script.write_text(f"#!/bin/sh\ntouch '{marker}'\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(LOCK_SCRIPT), "../escape", str(other_script), "--help"],
        env=_environment(tmp_path),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "scripts/staging_qa.sh up" in result.stdout
    assert not marker.exists()
    assert (tmp_path / "nextarget-staging.lock").is_file()


def test_lock_rejects_symlinked_lock_file(tmp_path: Path) -> None:
    protected_file = tmp_path / "protected"
    protected_file.write_text("unchanged", encoding="utf-8")
    (tmp_path / "nextarget-staging.lock").symlink_to(protected_file)

    result = subprocess.run(
        [sys.executable, str(LOCK_SCRIPT)],
        env=_environment(tmp_path),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode != 0
    assert protected_file.read_text(encoding="utf-8") == "unchanged"
