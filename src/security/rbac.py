"""
src/security/rbac.py
───────────────────────
Role-Based Access Control registry.
Maps roles → sets of scopes, and provides a permission checker
that can be used as a FastAPI dependency or called inside graph nodes.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Role:
    name: str
    scopes: frozenset[str]


# ── Role definitions ──────────────────────────────────────────────────────────
ROLES: dict[str, Role] = {
    "admin": Role(
        name="admin",
        scopes=frozenset(
            {
                "src:read",
                "src:write",
                "tool:run_command",
                "tool:fetch_website",
                "tool:read_skill",
                "memory:read",
                "memory:write",
                "subagent:invoke",
                "mcp:call",
            }
        ),
    ),
    "developer": Role(
        name="developer",
        scopes=frozenset(
            {
                "src:read",
                "src:write",
                "tool:fetch_website",
                "tool:read_skill",
                "memory:read",
                "memory:write",
                "subagent:invoke",
                "mcp:call",
            }
        ),
    ),
    "viewer": Role(
        name="viewer",
        scopes=frozenset({"src:read", "memory:read"}),
    ),
}


@dataclass
class RBACContext:
    """Resolved permission context for a request."""

    user_id: str
    roles: list[str] = field(default_factory=list)
    _resolved: set[str] = field(default_factory=set, init=False, repr=False)

    def __post_init__(self) -> None:
        for role_name in self.roles:
            if role := ROLES.get(role_name):
                self._resolved |= role.scopes

    def has(self, scope: str) -> bool:
        return scope in self._resolved

    def require(self, scope: str) -> None:
        """Raise PermissionError if the scope is missing."""
        if not self.has(scope):
            raise PermissionError(
                f"User '{self.user_id}' lacks required scope '{scope}'. "
                f"Granted: {sorted(self._resolved)}"
            )

    @property
    def all_scopes(self) -> list[str]:
        return sorted(self._resolved)
