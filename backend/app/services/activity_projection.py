"""Read-only activity projection: keep raw audit records, hide authentication material."""

import re
from app.services.workspace_export import scrub

PRIVATE = re.compile(r"(^|[_\W])(code|otp|pin|totp|session_id)($|[_\W])", re.I)
BEARER = re.compile(r"(?i)\bbearer\s+[^\s,;]+")
JWT = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")


def safe_details(value):
    def walk(item, depth=0):
        if depth > 8:
            return "[contenu tronqué]"
        if isinstance(item, dict):
            result = {
                str(key): (
                    "[credential excluded]"
                    if PRIVATE.search(str(key))
                    else walk(value, depth + 1)
                )
                for key, value in list(item.items())[:50]
            }
            if len(item) > 50:
                result["…"] = "[contenu tronqué]"
            return result
        if isinstance(item, list):
            return [walk(value, depth + 1) for value in item[:50]]
        if isinstance(item, str):
            return JWT.sub(
                "[credential excluded]", BEARER.sub("[credential excluded]", item)
            )[:2000]
        return item

    if value is None:
        return None
    projected = walk(scrub(value))
    return projected if isinstance(projected, dict) else {"value": projected}
