---
name: typesafe-ai
description: Use Jev for small, typed judgments over application state.
---

# TypeSafe / Jev

Use the local `typesafe_eval.py` bridge for live evaluations. It accepts JSON on
stdin and returns the TypeSafe response unchanged.

Use:

```bash
python3 typesafe_eval.py < examples/basic_request.json
```

The bridge calls `POST https://api.typesafe.ai/v1/systemone` with
`Authorization: Bearer $TYPESAFE_API_KEY`. It defaults to `jev-latest`, retries
transient 408, 429, 5xx, and 529 responses, and never prints the API key or
state in error messages.

Primitive choice:

- `choice`: one option from a defined set, with probabilities and confidence.
- `score`: an ordered rubric, with a probability-weighted score, legend,
  probabilities, and confidence.
- `noul`: probability that a yes/no statement is true. It has no confidence
  field.

Keep questions atomic, include all needed state, batch independent questions,
and keep policy, thresholds, calculations, and actions in code. Confidence is
uncertainty about the answer, not permission to act. Use conservative gates for
high-impact actions and validate thresholds on representative fixtures.
