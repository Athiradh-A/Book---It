"""Role inheritance for Book-It feature permissions.

Event approval decisions remain stage-specific and must use assigned roles,
not this inherited-role expansion.
"""
ROLE_HIERARCHY = {
    "STUDENT": 1,
    "FACULTY": 2,
    "WELFARE": 3,
    "DIRECTOR": 4,
    "EVENTS": 5,
}


def effective_roles(roles: list[str]) -> set[str]:
    """Return lower-level feature roles inherited from assigned workflow roles."""
    result = set(roles)
    highest = max((ROLE_HIERARCHY.get(role, 0) for role in roles), default=0)
    result.update(role for role, level in ROLE_HIERARCHY.items() if level <= highest)
    return result
