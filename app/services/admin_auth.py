"""Password hashing and verification for the read-only admin page."""

import base64
import hashlib
import hmac
import secrets
from typing import Final


SCRYPT_PREFIX: Final[str] = "scrypt"
SCRYPT_N: Final[int] = 2**14
SCRYPT_R: Final[int] = 8
SCRYPT_P: Final[int] = 1
SALT_BYTES: Final[int] = 16
KEY_BYTES: Final[int] = 32


def hash_admin_password(password: str) -> str:
    """Create a salted scrypt verifier for an administrator password.

    Args:
        password: Plain password entered locally by the administrator.

    Returns:
        A versioned verifier safe to store as an environment secret.
    """
    if not password:
        raise ValueError("Password must not be empty")

    salt = secrets.token_bytes(SALT_BYTES)
    derived_key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=KEY_BYTES,
    )
    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii")
    encoded_key = base64.urlsafe_b64encode(derived_key).decode("ascii")
    return (
        f"{SCRYPT_PREFIX}${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}"
        f"${encoded_salt}${encoded_key}"
    )


def verify_admin_password(password: str, verifier: str) -> bool:
    """Verify a password against a versioned scrypt verifier.

    Malformed or unsupported verifiers fail closed rather than leaking
    configuration details to the caller.

    Args:
        password: Password received through HTTP Basic over HTTPS.
        verifier: Encoded verifier from ``ADMIN_PASSWORD_HASH``.

    Returns:
        Whether the password matches the verifier.
    """
    try:
        prefix, raw_n, raw_r, raw_p, encoded_salt, encoded_key = verifier.split("$")
        if prefix != SCRYPT_PREFIX:
            return False
        n, r, p = int(raw_n), int(raw_r), int(raw_p)
        if (n, r, p) != (SCRYPT_N, SCRYPT_R, SCRYPT_P):
            return False
        salt = base64.b64decode(encoded_salt, altchars=b"-_", validate=True)
        expected_key = base64.b64decode(encoded_key, altchars=b"-_", validate=True)
        if len(salt) != SALT_BYTES or len(expected_key) != KEY_BYTES:
            return False
        actual_key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=len(expected_key),
        )
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(actual_key, expected_key)
