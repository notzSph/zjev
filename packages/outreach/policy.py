"""Conservative routing for outreach intelligence results."""

from typing import Any

from .calibration import Z_CALIBRATION_VERSION


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


def derive_outreach_policy(result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(result, dict) or not isinstance(result.get("answers"), dict):
        raise ValueError("result must contain an answers object")
    answers = result["answers"]
    personalization = _score(answers, "personalization_evidence")
    generic_risk = _score(answers, "generic_risk")
    icp_fit = _score(answers, "icp_fit")
    buyer_relevance = _score(answers, "buyer_relevance")
    buying_signal = _score(answers, "buying_signal")
    account_safety_risk = _score(answers, "account_safety_risk")
    readiness = _noul(answers, "outreach_readiness")
    unsupported = _noul(answers, "unsupported_claim_risk")
    angle = _answer(answers, "best_outreach_angle").get("choice")
    cta = _answer(answers, "cta_type").get("choice")
    missing = [
        name for name, value in {
            "personalization_evidence": personalization,
            "generic_risk": generic_risk,
            "icp_fit": icp_fit,
            "buyer_relevance": buyer_relevance,
            "buying_signal": buying_signal,
            "account_safety_risk": account_safety_risk,
            "outreach_readiness": readiness,
            "unsupported_claim_risk": unsupported,
        }.items()
        if value is None
    ]
    if missing:
        raise ValueError(f"missing outreach answers: {', '.join(missing)}")
    confidence_values = [
        _confidence(answers, name)
        for name in (
            "icp_fit", "buyer_relevance", "buying_signal",
            "personalization_evidence", "generic_risk",
            "account_safety_risk", "outreach_readiness",
        )
    ]
    confidence_values = [value for value in confidence_values if value is not None]
    confidence_floor = min(confidence_values) if confidence_values else None
    if confidence_floor is None or confidence_floor < 0.60:
        confidence_band = "fallback"
    elif confidence_floor < 0.85:
        confidence_band = "review"
    else:
        confidence_band = "proceed"

    if confidence_band == "fallback":
        action = "research_more"
    elif account_safety_risk >= 3.0:
        action = "research_more"
    elif icp_fit < 2.0 or buyer_relevance < 2.0:
        action = "research_more"
    elif buying_signal < 2.0 or readiness is not True or angle == "no_defensible_angle":
        action = "research_more"
    elif unsupported is True or generic_risk >= 3.0 or personalization < 3.0:
        action = "human_review"
    elif cta == "no_cta":
        action = "human_review"
    else:
        action = "draft_for_review"
    return {
        "recommended_action": action,
        "calibration_version": Z_CALIBRATION_VERSION,
        "confidence_floor": confidence_floor,
        "confidence_band": confidence_band,
        "human_approval_required": True,
        "auto_send": False,
        "signals": {
            "personalization_evidence": personalization,
            "generic_risk": generic_risk,
            "icp_fit": icp_fit,
            "buyer_relevance": buyer_relevance,
            "buying_signal": buying_signal,
            "account_safety_risk": account_safety_risk,
            "outreach_readiness": readiness,
            "unsupported_claim_risk": unsupported,
            "best_outreach_angle": angle,
            "cta_type": cta,
        },
    }
