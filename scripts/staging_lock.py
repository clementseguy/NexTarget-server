#!/usr/bin/env python3
"""Hold a host-local lock while the staging launcher runs."""

import fcntl
import os
from pathlib import Path
import sys
import tempfile


def main() -> None:
    """Replace this process with the locked Bash launcher."""
    project, script, *arguments = sys.argv[1:]
    lock_path = Path(tempfile.gettempdir()) / f"{project}.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(f"Staging project {project} is already in use.") from None
    os.set_inheritable(fd, True)
    environment = dict(os.environ, NEXTARGET_STAGING_LOCKED="1")
    os.execve("/bin/bash", ["/bin/bash", script, *arguments], environment)


if __name__ == "__main__":
    main()
