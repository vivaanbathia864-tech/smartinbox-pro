# server/auth.py
# ─────────────────────────────────────────────────────────────────
#  OAuth2 + JWT Authentication Layer
#  Protects all OpenEnv server endpoints
# ─────────────────────────────────────────────────────────────────

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from functools import wraps
from typing import Callable, Optional

try:
    import jwt
    from fastapi import HTTPException, Security
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
    _HAS_DEPS = True
except ImportError:
    _HAS_DEPS = False


SECRET_KEY  = os.environ.get("JWT_SECRET_KEY", "change-me-in-prod-use-256bit-key")
ALGORITHM   = "HS256"
TOKEN_TTL   = int(os.environ.get("JWT_TTL_SECONDS", "3600"))

# OAuth2 provider config (Google / GitHub / custom)
OAUTH2_CLIENT_ID     = os.environ.get("OAUTH2_CLIENT_ID", "")
OAUTH2_CLIENT_SECRET = os.environ.get("OAUTH2_CLIENT_SECRET", "")
OAUTH2_REDIRECT_URI  = os.environ.get("OAUTH2_REDIRECT_URI", "http://localhost:7860/auth/callback")


@dataclass
class TokenPayload:
    sub: str           # user id / email
    exp: float
    scopes: list
    iat: float


class JWTAuthenticator:
    """
    Issues and verifies JWT tokens for the OpenEnv API server.

    Flow:
    1. Agent POSTs to /auth/token with client_id + client_secret
    2. Server returns a signed JWT
    3. All subsequent /env/* calls include  Authorization: Bearer <token>
    4. verify_token() is called as a FastAPI dependency
    """

    def issue_token(self, subject: str, scopes: list = None) -> str:
        now = time.time()
        payload = {
            "sub": subject,
            "iat": now,
            "exp": now + TOKEN_TTL,
            "scopes": scopes or ["env:step", "env:reset", "env:state"],
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    def verify_token(self, token: str) -> TokenPayload:
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return TokenPayload(
                sub=data["sub"],
                exp=data["exp"],
                scopes=data.get("scopes", []),
                iat=data["iat"],
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {e}")


# FastAPI dependency (only usable if FastAPI is installed)
_bearer = HTTPBearer() if _HAS_DEPS else None
_auth   = JWTAuthenticator()


def require_auth(credentials: "HTTPAuthorizationCredentials" = None):
    """FastAPI dependency that validates Bearer token."""
    if not _HAS_DEPS:
        return None
    token = credentials.credentials
    try:
        return _auth.verify_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


# ── Rate limiter (token bucket) ───────────────────────────────────
class RateLimiter:
    """
    Simple per-subject token bucket rate limiter.
    Production: replace with Redis INCR + EXPIRE.
    """
    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self._buckets: dict = {}

    def is_allowed(self, subject: str) -> bool:
        now = time.time()
        window_start = now - 60
        events = self._buckets.get(subject, [])
        events = [t for t in events if t > window_start]
        if len(events) >= self.rpm:
            return False
        events.append(now)
        self._buckets[subject] = events
        return True


rate_limiter = RateLimiter(requests_per_minute=120)
