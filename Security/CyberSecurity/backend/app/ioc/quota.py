"""Daily per-tenant Groq call quota (in-memory, Sprint-1).

Over-cap calls are skipped with ``ai_skipped: quota`` so heuristic stands.
For multi-worker deploys replace with Redis INCR + TTL.
"""

from __future__ import annotations

import os
from datetime import date

_CAPS: dict[str, int] = {}


def daily_cap() -> int:
    try:
        return max(1, int(os.getenv("GROQ_DAILY_CAP", "100")))
    except ValueError:
        return 100


def _key(tenant_id: str) -> str:
    return f"{date.today().isoformat()}:{tenant_id}"


def check_and_bump(tenant_id: str) -> bool:
    """Return True if call allowed (and count it), False when over quota."""
    k = _key(str(tenant_id))
    if _CAPS.get(k, 0) >= daily_cap():
        return False
    _CAPS[k] = _CAPS.get(k, 0) + 1
    return True


def reset() -> None:
    _CAPS.clear()
