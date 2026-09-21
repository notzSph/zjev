"""Load the documented basic Choice, Score, and Noul example."""

import json
from pathlib import Path


def load_basic_request() -> dict:
    path = Path(__file__).parents[2] / "examples" / "basic_request.json"
    return json.loads(path.read_text(encoding="utf-8"))
