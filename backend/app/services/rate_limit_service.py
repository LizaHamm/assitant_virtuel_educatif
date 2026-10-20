from datetime import datetime, timezone, timedelta
from threading import Lock


# ============================================================
# US-013 — RATE LIMITING
# ============================================================

MAX_REQUESTS = 10
WINDOW_SECONDS = 60


_requests = {}

_lock = Lock()


def check_rate_limit(session_id):
    """
    Autorise maximum 10 questions par minute
    pour une même session.

    Les sessions sont indépendantes.
    """

    now = datetime.now(timezone.utc)

    with _lock:

        if session_id not in _requests:
            _requests[session_id] = []

        cutoff = now - timedelta(
            seconds=WINDOW_SECONDS
        )

        _requests[session_id] = [
            timestamp
            for timestamp in _requests[session_id]
            if timestamp > cutoff
        ]

        if len(_requests[session_id]) >= MAX_REQUESTS:

            return {
                "allowed": False,
                "remaining": 0,
            }

        _requests[session_id].append(now)

        remaining = (
            MAX_REQUESTS
            - len(_requests[session_id])
        )

        return {
            "allowed": True,
            "remaining": remaining,
        }