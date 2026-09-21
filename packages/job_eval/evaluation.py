"""Build evidence-grounded TypeSafe requests for job evaluation."""

from typing import Any

SCORE_LEVELS = [
    "No credible evidence of fit",
    "Some adjacent evidence but major gaps",
    "Moderate fit with meaningful transferable evidence",
    "Strong fit with limited gaps",
    "Very strong direct fit",
]
EVALUATION_PROTOCOL = (
    "Evaluate only the supplied CV and job description. Treat missing or vague "
    "information as missing evidence, never as proof of experience. Separate "
    "direct evidence from transferable evidence. Do not infer tools, scope, "
    "seniority, ownership, outcomes, or credentials that are not stated. "
    "Use the full 0-4 score range. Keep each judgment atomic and independent."
)


def _score(instructions: str) -> dict[str, Any]:
    return {"type": "score", "instructions": instructions, "criteria": SCORE_LEVELS}


def _noul(instructions: str, true_label: str, false_label: str) -> dict[str, Any]:
    return {"type": "noul", "instructions": instructions, "criteria": {"true": true_label, "false": false_label}}


def build_job_eval_request(cv: str, job_description: str, model: str = "jev-latest") -> dict[str, Any]:
    if not isinstance(cv, str) or not cv.strip():
        raise ValueError("cv must be a non-empty string")
    if not isinstance(job_description, str) or not job_description.strip():
        raise ValueError("job_description must be a non-empty string")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("model must be a non-empty string")

    score_questions = {
        "overall_fit": "How strong is the candidate's demonstrated overall fit for this role, after considering the separate dimensions below?",
        "requirement_coverage": "How much of the role's stated core requirements are explicitly covered by credible evidence in the CV?",
        "technical_fit": "How directly does the CV evidence the technical capabilities, methods, and systems work required by the job?",
        "architecture_fit": "How directly does the CV evidence the architecture, design, scale, performance, security, or platform responsibilities required by the job?",
        "leadership_fit": "How directly does the CV evidence the ownership, technical leadership, mentoring, and decision-making expected by the job?",
        "client_delivery_fit": "How directly does the CV evidence client-facing delivery, stakeholder management, consulting, proposals, or communication required by the job?",
        "quality_and_governance_fit": "How directly does the CV evidence maintainability, quality, governance, risk, compliance, change management, or operational discipline relevant to the job?",
        "seniority_fit": "How well does the demonstrated scope, ownership, and career level in the CV match the seniority and autonomy required by the job?",
        "evidence_quality": "How specific, recent, outcome-oriented, and credible is the CV evidence for judging this role, independent of unlisted experience?",
    }
    questions: dict[str, Any] = {name: _score(text) for name, text in score_questions.items()}
    questions.update({
        "application_strategy": {
            "type": "choice",
            "instructions": "What is the most defensible next application action based only on the evidence?",
            "criteria": {
                "apply_now": "The current CV supports applying without material tailoring",
                "tailor_first": "Tailor the CV first to expose relevant evidence or address presentation gaps",
                "stretch": "Apply as a deliberate stretch because material evidence gaps remain",
                "skip": "Do not prioritize this application because the role is materially misaligned",
            },
        },
        "primary_positioning": {
            "type": "choice",
            "instructions": "Which positioning is most defensible for this application?",
            "criteria": {
                "direct_match": "Present as a direct match for the central work",
                "transferable_match": "Present adjacent experience and clearly name the transfer",
                "growth_candidate": "Present as capable of growing into the role",
                "not_recommended": "Do not position the candidate for this role",
            },
        },
        "material_evidence_gap": _noul("Is at least one central requirement absent, vague, or only weakly transferable in the CV?", "A central requirement lacks credible CV evidence", "The central requirements have credible CV evidence"),
        "critical_requirement_gap": _noul("Is there a gap on a requirement likely decisive for screening or successful performance?", "A likely decisive requirement is unsupported or materially weak", "No likely decisive requirement is materially unsupported"),
        "seniority_mismatch": _noul("Does the role require a materially different level of scope, ownership, or autonomy than the CV demonstrates?", "The demonstrated level materially differs from the role level", "The demonstrated level is reasonably aligned with the role level"),
        "overclaim_risk": _noul("Would presenting the candidate as a direct match overstate seniority, ownership, outcomes, or direct experience?", "The positioning would overstate the supplied evidence", "The positioning is supported by the supplied evidence"),
        "resume_tailoring_needed": _noul("Would targeted CV changes materially improve truthful evidence retrieval for this role?", "Relevant evidence exists but is buried, vague, or poorly targeted", "The CV exposes relevant evidence clearly enough"),
    })
    return {"model": model, "state": {"cv": cv, "job_description": job_description, "evaluation_protocol": EVALUATION_PROTOCOL}, "questions": questions}
