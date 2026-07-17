"""
src/graph/nodes/auth.py
──────────────────────────
Auth node: verifies the JWT, resolves RBAC permissions, and
injects AuthContext into AgentState before any other node runs.
"""

from __future__ import annotations

import logging
from typing import Any

from src.config import get_settings
from src.graph.state import AgentState, AuthContext, Permission
from src.observability.instrumentation import traced_node
from src.security.jwt import JWTService
from src.security.rbac import ROLES, RBACContext

logger = logging.getLogger(__name__)


@traced_node("auth")
def auth_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node — First node in the graph.
    Validates the bearer token and builds AuthContext.
    Raises on invalid/expired tokens (LangGraph will catch and error the run).
    """
    token = state.raw_token
    if not token:
        raise PermissionError("No authentication token provided in state.raw_token.")

    svc = JWTService(get_settings().security)
    claims = svc.verify_token(token)

    # Resolve RBAC
    rbac = RBACContext(user_id=claims.sub, roles=claims.roles)

    permissions = [
        Permission(role=role_name, scopes=list(ROLES[role_name].scopes))
        for role_name in claims.roles
        if role_name in ROLES
    ]

    auth = AuthContext(
        user_id=claims.sub,
        session_id=state.thread_id or claims.sub,
        permissions=permissions,
        claims=claims.extra,
    )

    logger.info(
        "Auth OK: user=%s roles=%s scopes=%d",
        claims.sub,
        claims.roles,
        len(rbac.all_scopes),
    )

    return {"auth": auth}
