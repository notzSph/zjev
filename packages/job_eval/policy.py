"""Conservative, deterministic routing for job-evaluation results."""

from typing import Any

WEIGHTS = {
    "overall_fit": 0.15, "requirement_coverage": 0.15, "technical_fit": 0.15,
    "architecture_fit": 0.15, "leadership_fit": 0.10, "client_delivery_fit": 0.10,
    "quality_and_governance_fit": 0.05, "seniority_fit": 0.10, "evidence_quality": 0.05,
}


def _answer(answers: dict[str, Any], name: str) -> dict[str, Any]:
    value = answers.get(name)
    return value if isinstance(value, dict) else {}


def _score(answers: dict[str, Any], name: str) -> float | None:
    value = _answer(answers, name).get("score")
    return float(value) if isinstance(value, (int, float)) else None


def _confidence(answers: dict[str, Any], name: str) -> float | None:
    value = _answer(answers, name).get("confidence")
    return float(value) if isinstance(value, (int, float)) else None


def _noul(answers: dict[str, Any], name: str) -> bool | None:
    value = _answer(answers, name).get("noul")
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    return None


def derive_job_eval_policy(result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(result, dict) or not isinstance(result.get("answers"), dict):
        raise ValueError("result must contain an answers object")
    answers = result["answers"]
    scores = {name: _score(answers, name) for name in WEIGHTS}
    missing = [name for name, value in scores.items() if value is None or not 0 <= value <= 4]
    if missing:
        raise ValueError(f"missing or invalid score answers: {', '.join(missing)}")
    weighted_fit = sum(scores[name] * weight for name, weight in WEIGHTS.items())
    critical = ["overall_fit", "requirement_coverage", "technical_fit", "architecture_fit", "seniority_fit"]
    confidences = [_confidence(answers, name) for name in critical]
    confidences = [value for value in confidences if value is not None]
    confidence_floor = min(confidences) if confidences else None
    model_strategy = _answer(answers, "application_strategy").get("choice")
    model_positioning = _answer(answers, "primary_positioning").get("choice")
    critical_gap = _noul(answers, "critical_requirement_gap")
    seniority_mismatch = _noul(answers, "seniority_mismatch")
    overclaim_risk = _noul(answers, "overclaim_risk")
    tailoring_needed = _noul(answers, "resume_tailoring_needed")
    if confidence_floor is None or confidence_floor < 0.60:
        confidence_band = "fallback"
    elif confidence_floor < 0.85:
        confidence_band = "review"
    else:
        confidence_band = "proceed"
    if confidence_band == "fallback":
        action = "manual_review"
    elif model_strategy == "skip" or weighted_fit < 1.5:
        action = "skip"
    elif critical_gap is True and weighted_fit < 3.0:
        action = "manual_review"
    elif overclaim_risk is True or seniority_mismatch is True or tailoring_needed is True:
        action = "tailor_first"
    elif model_strategy == "stretch":
        action = "stretch"
    elif weighted_fit >= 3.0 and model_strategy == "apply_now":
        action = "apply_now"
    else:
        action = "manual_review"
    return {
        "weighted_fit": round(weighted_fit, 3), "confidence_floor": confidence_floor,
        "confidence_band": confidence_band, "recommended_action": action,
        "model_strategy": model_strategy, "model_positioning": model_positioning,
        "guardrails": {"critical_requirement_gap": critical_gap, "seniority_mismatch": seniority_mismatch, "overclaim_risk": overclaim_risk, "resume_tailoring_needed": tailoring_needed},
    }
