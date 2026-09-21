"""Build the first job evaluation TypeSafe request."""

from typing import Any

SCORE_LEVELS = [
    "No credible evidence of fit",
    "Some adjacent evidence but major gaps",
    "Moderate fit with meaningful transferable evidence",
    "Strong fit with limited gaps",
    "Very strong direct fit",
]


def _score(instructions: str) -> dict[str, Any]:
    return {"type": "score", "instructions": instructions, "criteria": SCORE_LEVELS}


def build_job_eval_request(cv: str, job_description: str, model: str = "jev-latest") -> dict[str, Any]:
    if not isinstance(cv, str) or not cv.strip():
        raise ValueError("cv must be a non-empty string")
    if not isinstance(job_description, str) or not job_description.strip():
        raise ValueError("job_description must be a non-empty string")
    return {
        "model": model,
        "state": {"cv": cv, "job_description": job_description},
        "questions": {
            "overall_fit": _score("How strong is the candidate's demonstrated fit for this role, considering only evidence in the CV?"),
            "technical_fit": _score("How directly does the CV evidence the technical capabilities and systems work required by the job?"),
            "leadership_fit": _score("How directly does the CV evidence the leadership, ownership, coordination, or mentoring expected by the job?"),
            "client_delivery_fit": _score("How directly does the CV evidence client-facing delivery, consulting, stakeholder work, or technical proposals required by the job?"),
            "quality_and_governance_fit": _score("How directly does the CV evidence quality, scalability, security, maintainability, governance, or change management relevant to the job?"),
            "application_strategy": {
                "type": "choice",
                "instructions": "What is the most defensible application strategy based only on the CV evidence?",
                "criteria": {
                    "apply_now": "Apply with the current CV because the evidence is strong enough",
                    "tailor_first": "Apply after tailoring the CV to expose relevant evidence and close presentation gaps",
                    "stretch": "Apply as a stretch role despite material evidence gaps",
                    "skip": "Do not prioritize this application because the role is materially misaligned",
                },
            },
            "material_evidence_gap": {
                "type": "noul",
                "instructions": "Does the CV lack explicit evidence for one or more central requirements of the job?",
                "criteria": {"true": "A central requirement is absent, vague, or only weakly transferable", "false": "The CV clearly demonstrates the central requirements"},
            },
            "overclaim_risk": {
                "type": "noul",
                "instructions": "Would positioning the candidate as a direct match risk overstating the evidence in the CV?",
                "criteria": {"true": "The positioning would overstate seniority, ownership, or direct experience", "false": "The positioning is supported by explicit CV evidence"},
            },
        },
    }
