#!/usr/bin/env python3
"""Hold a host-local lock while the staging launcher runs."""

import fcntl
import os
from pathlib import Path
import tempfile


def main() -> None:
    """Replace this process with the locked Bash launcher."""
    lock_path = Path(tempfile.gettempdir()) / "nextarget-staging.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("A staging operation is already in progress.") from None
    os.set_inheritable(fd, True)
    environment = dict(os.environ, NEXTARGET_STAGING_LOCKED="1")
    script = Path(__file__).resolve().with_name("staging_qa.sh")
    os.execve("/bin/bash", ["/bin/bash", str(script)], environment)


if __name__ == "__main__":
    main()
