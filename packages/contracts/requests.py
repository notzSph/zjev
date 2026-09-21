from typing import Any


class InputError(ValueError):
    """Raised when a Jev request violates the public input contract."""


def validate_request(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise InputError("request must be a JSON object")
    if "state" not in payload:
        raise InputError("missing required field: state")
    if not isinstance(payload["state"], (str, dict, list)):
        raise InputError("state must be a string, object, or array")
    questions = payload.get("questions")
    if not isinstance(questions, dict) or not questions:
        raise InputError("questions must be a non-empty object")

    for question_id, question in questions.items():
        if not isinstance(question_id, str) or not question_id:
            raise InputError("question ids must be non-empty strings")
        if not isinstance(question, dict):
            raise InputError(f"question {question_id!r} must be an object")
        question_type = question.get("type")
        if question_type not in {"choice", "score", "noul"}:
            raise InputError(f"question {question_id!r} has invalid type")
        if "instructions" not in question:
            raise InputError(f"question {question_id!r} is missing instructions")
        if question_type == "choice":
            criteria = question.get("criteria")
            if not isinstance(criteria, dict) or not criteria:
                raise InputError(f"choice {question_id!r} needs a non-empty criteria object")
            if len(criteria) > 255:
                raise InputError(f"choice {question_id!r} has more than 255 options")
        elif question_type == "score":
            criteria = question.get("criteria")
            if not isinstance(criteria, list) or len(criteria) < 2 or len(criteria) > 10:
                raise InputError(f"score {question_id!r} needs 2 to 10 criteria levels")
        elif "criteria" in question and not isinstance(question["criteria"], dict):
            raise InputError(f"noul {question_id!r} criteria must be an object")

    return {
        "state": payload["state"],
        "model": payload.get("model", "jev-latest"),
        "questions": questions,
    }
