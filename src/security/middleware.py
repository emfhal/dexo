"""
src/security/middleware.py
─────────────────────────────
FastAPI middleware + reusable dependency for Bearer-token authentication.
Injects RBACContext into the request state so any endpoint/WebSocket
can access it without re-parsing the token.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config import get_settings
from src.security.jwt import JWTService
from src.security.rbac import RBACContext

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=True)


def _get_jwt_service() -> JWTService:
    return JWTService(get_settings().security)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
    jwt_svc: Annotated[JWTService, Depends(_get_jwt_service)],
) -> RBACContext:
    """
    FastAPI dependency.
    Validates the Bearer token and returns a fully resolved RBACContext.

    Usage:
        @router.post("/chat")
        async def chat(
            body: ChatRequest,
            rbac: Annotated[RBACContext, Depends(get_current_user)],
        ):
            rbac.require("src:write")
            ...
    """
    claims = jwt_svc.verify_token(credentials.credentials)
    context = RBACContext(user_id=claims.sub, roles=claims.roles)
    logger.debug("Authenticated user=%s roles=%s", claims.sub, claims.roles)
    return context


def require_scope(scope: str) -> Callable:
    """
    Factory that produces a dependency enforcing a specific scope.

    Usage:
        @router.post("/run-command")
        async def run_cmd(
            _: Annotated[None, Depends(require_scope("tool:run_command"))],
        ):
            ...
    """
    from typing import Annotated as Ann  # noqa: PLC0415

    async def _check(rbac: Ann[RBACContext, Depends(get_current_user)]) -> None:
        if not rbac.has(scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope '{scope}' required.",
            )

    return Depends(_check)


# ── Starlette middleware for raw request logging ──────────────────────────────

from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402

if TYPE_CHECKING:
    from starlette.requests import Request as StarletteRequest
    from starlette.responses import Response


class AuthLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with user identity if authenticated."""

    async def dispatch(self, request: StarletteRequest, call_next: Callable) -> Response:
        user_id = "anonymous"
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                svc = _get_jwt_service()
                claims = svc.verify_token(auth_header[7:])
                user_id = claims.sub
            except Exception:  # noqa: BLE001
                pass

        logger.info("%s %s user=%s", request.method, request.url.path, user_id)
        response = await call_next(request)
        return response
