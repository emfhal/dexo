"""
src/security/jwt.py
──────────────────────
JWT verification and claims extraction using python-jose.
Supports both HS256 and RS256. Raises HTTPException on any failure
so it can be used as a FastAPI dependency directly.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, status
from jose import JWTError, jwt  # type: ignore[import-untyped]
from pydantic import BaseModel

if TYPE_CHECKING:
    from src.config import SecurityConfig


class TokenClaims(BaseModel):
    sub: str  # user_id
    exp: datetime
    iat: datetime
    roles: list[str] = []
    scopes: list[str] = []
    extra: dict[str, Any] = {}


class JWTService:
    def __init__(self, cfg: SecurityConfig) -> None:
        self._secret = cfg.jwt_secret_key
        self._algo = cfg.jwt_algorithm
        self._expire_minutes = cfg.jwt_access_token_expire_minutes

    # ── Encoding ──────────────────────────────────────────────────────────────
    def create_access_token(
        self,
        subject: str,
        roles: list[str] | None = None,
        scopes: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> str:
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "sub": subject,
            "iat": now,
            "exp": now + timedelta(minutes=self._expire_minutes),
            "roles": roles or [],
            "scopes": scopes or [],
            **(extra or {}),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algo)  # type: ignore[no-any-return]

    # ── Decoding / Verification ───────────────────────────────────────────────
    def verify_token(self, token: str) -> TokenClaims:
        try:
            raw = jwt.decode(token, self._secret, algorithms=[self._algo])
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication token: {exc}",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        exp = raw.get("exp")
        iat = raw.get("iat")

        if not exp or not iat:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing required time claims.",
            )

        known_keys = {"sub", "exp", "iat", "roles", "scopes"}
        return TokenClaims(
            sub=raw["sub"],
            exp=datetime.fromtimestamp(exp, tz=UTC),
            iat=datetime.fromtimestamp(iat, tz=UTC),
            roles=raw.get("roles", []),
            scopes=raw.get("scopes", []),
            extra={k: v for k, v in raw.items() if k not in known_keys},
        )
