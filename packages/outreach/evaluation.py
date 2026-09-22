"""Build evidence-grounded Jev requests for human-reviewed outreach."""

from typing import Any

from .calibration import DISQUALIFIERS, ICP, OFFER_LANES, OPERATING_RULES, Z_CALIBRATION_VERSION

SCORE_LEVELS = [
    "No credible evidence",
    "Weak or generic evidence",
    "Some relevant evidence",
    "Strong specific evidence",
    "Very strong direct evidence",
]

PROTOCOL = (
    "Use only the supplied profile, activity, interactions, offer, and proof assets. "
    "Treat missing information as missing. Do not invent familiarity, pain, authority, "
    "intent, outcomes, or shared context. Produce a useful brief for a human writer, "
    "not a finished message and never an instruction to auto-send."
)


def _score(instructions: str) -> dict[str, Any]:
    return {"type": "score", "instructions": instructions, "criteria": SCORE_LEVELS}


def _choice(instructions: str, criteria: dict[str, str]) -> dict[str, Any]:
    return {"type": "choice", "instructions": instructions, "criteria": criteria}


def _noul(instructions: str) -> dict[str, Any]:
    return {
        "type": "noul",
        "instructions": instructions,
        "criteria": {"true": "Yes", "false": "No"},
    }


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_text(value: Any, name: str) -> str:
    if value is None:
        return "Not supplied"
    return _text(value, name)


def _assets(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError("proof_assets must be a non-empty list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError("proof_assets must contain non-empty strings")
    return [item.strip() for item in value]


def build_outreach_request(
    target_profile: str,
    linkedin_activity: str,
    offer: str,
    proof_assets: list[str],
    prior_interactions: str | None = None,
    model: str = "jev-latest",
) -> dict[str, Any]:
    if not isinstance(model, str) or not model.strip():
        raise ValueError("model must be a non-empty string")
    assets = _assets(proof_assets)
    asset_criteria = {f"asset_{index}": asset for index, asset in enumerate(assets)}
    questions: dict[str, Any] = {
        "best_outreach_angle": _choice(
            "Which angle is best supported by the supplied evidence?",
            {
                "relevant_problem": "A specific problem or signal supported by the evidence",
                "relevant_result": "A relevant result or proof point supported by the evidence",
                "relevant_insight": "A useful insight tied to the target's context",
                "no_defensible_angle": "No specific angle is supported yet",
            },
        ),
        "icp_fit": _score(
            "How well does the target match the calibrated geography, company profile, buyer titles, and priority signals?"
        ),
        "buyer_relevance": _score(
            "How credible is this person as a buyer or influential stakeholder for one of the calibrated offer lanes?"
        ),
        "buying_signal": _score(
            "How strong is the evidence of a current problem, initiative, event, or urgency that could justify contact now?"
        ),
        "account_safety_risk": _score(
            "How likely is this action to create LinkedIn account, reputation, or spam risk under the calibrated low-volume manual rules?"
        ),
        "relevant_proof_asset": _choice(
            "Which supplied proof asset is most relevant, if any?",
            {"none": "No supplied proof asset is defensible", **asset_criteria},
        ),
        "personalization_evidence": _score(
            "How specific and credible is the evidence for personalizing outreach?"
        ),
        "likely_objection": _choice(
            "What is the most likely objection or friction point, based only on the evidence?",
            {
                "relevance": "The message may not be relevant enough",
                "timing": "Timing or priority may be weak",
                "trust": "The claim or sender may lack trust evidence",
                "effort": "The proposed next step may feel costly or burdensome",
                "unknown": "No defensible objection can be identified",
            },
        ),
        "outreach_readiness": _noul(
            "Is there enough evidence to prepare a human-reviewed outreach draft now?"
        ),
        "generic_risk": _score(
            "How likely is the outreach to sound generic if written from this evidence?"
        ),
        "unsupported_claim_risk": _noul(
            "Would a direct outreach claim likely overstate what the evidence supports?"
        ),
        "cta_type": _choice(
            "What call to action is least presumptuous and best supported?",
            {
                "share_resource": "Offer a relevant resource or proof asset",
                "ask_context": "Ask one narrow context question",
                "suggest_conversation": "Suggest a short conversation",
                "no_cta": "Do not propose a CTA yet",
            },
        ),
    }
    return {
        "model": model.strip(),
        "state": {
            "target_profile": _text(target_profile, "target_profile"),
            "linkedin_activity": _text(linkedin_activity, "linkedin_activity"),
            "prior_interactions": _optional_text(prior_interactions, "prior_interactions"),
            "offer": _text(offer, "offer"),
            "proof_assets": assets,
            "outreach_protocol": PROTOCOL,
            "z_calibration": {
                "version": Z_CALIBRATION_VERSION,
                "icp": ICP,
                "offer_lanes": OFFER_LANES,
                "operating_rules": OPERATING_RULES,
                "disqualifiers": DISQUALIFIERS,
            },
        },
        "questions": questions,
    }
