"""Password hashing and JWT issuing/verification.

Two token types are used:

* access  - short lived, sent as `Authorization: Bearer <token>` on every
            authenticated request.
* refresh - long lived, sent only to `POST /auth/refresh` to get a new
            access token without logging in again.

Both are signed with the same secret; the `type` claim inside the token
decides which endpoints accept it, so an access token can never be
swapped in for a refresh and vice versa.

Known limitation (documented on purpose): tokens are stateless, so
"logout" only tells the client to forget them - a stolen token stays
valid until it expires.  If that ever matters, add a Redis denylist of
`jti` values checked in `get_current_user`.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

ACCESS = "access"
REFRESH = "refresh"


class TokenError(Exception):
    """Raised when a token is missing, expired, malformed or of the wrong type."""


# --- passwords --------------------------------------------------------------

def hash_password(password: str) -> str:
    """bcrypt hash, ready to store in `users.password_hash`."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # Corrupted hash row - treat as "wrong password", never as a crash.
        return False


# --- tokens -----------------------------------------------------------------

def _create_token(user_id: int, token_type: str, lifetime: timedelta) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    jti = uuid.uuid4().hex
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "jti": jti,
        "iat": now,
        "nbf": now,
        "exp": now + lifetime,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def create_access_token(user_id: int) -> str:
    token, _ = _create_token(
        user_id, ACCESS, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return token


def create_refresh_token(user_id: int) -> str:
    token, _ = _create_token(
        user_id, REFRESH, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    return token


def decode_token(token: str, expected_type: str) -> dict:
    """Decode and validate a token, returning its claims.

    Raises TokenError for anything that is not a valid token of the
    expected type - callers turn that into an HTTP 401.
    """
    try:
        claims = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "type", "jti"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc

    if claims.get("type") != expected_type:
        raise TokenError(f"expected a {expected_type} token")

    try:
        claims["user_id"] = int(claims["sub"])
    except (KeyError, ValueError) as exc:
        raise TokenError("token subject is not a user id") from exc
    return claims


def new_client_secret(length: int = 32) -> str:
    """Random hex string - used for freshly generated JWT secrets."""
    return secrets.token_hex(length)
