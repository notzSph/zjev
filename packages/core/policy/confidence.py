"""Small, reusable confidence policy primitives.

The thresholds are intentionally explicit and conservative. They are policy,
not claims about Jev accuracy or permission to perform an action.
"""


def confidence_band(confidence: float, *, low: float = 0.5, high: float = 0.9) -> str:
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")
    if not 0 <= low <= high <= 1:
        raise ValueError("thresholds must satisfy 0 <= low <= high <= 1")
    if confidence < low:
        return "fallback"
    if confidence < high:
        return "review"
    return "proceed"
