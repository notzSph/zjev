# zjev

[![Version](https://img.shields.io/badge/version-0.0.1--alpha-orange.svg)](https://semver.org/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-supported-2496ED.svg)](https://www.docker.com/)
[![Status](https://img.shields.io/badge/status-alpha-yellow.svg)](https://en.wikipedia.org/wiki/Software_release_life_cycle)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

This is a narrow TypeSafe bridge. It leaves OpenClaw configuration
untouched and exposes all documented basic primitives through one JSON-in/JSON-
out command.

## License

Licensed under the MIT License. See [LICENSE](LICENSE).

## Live setup

Export the key server-side, then run:

```bash
export JEV_API_KEY='...'
python3 apps/cli/main.py < examples/basic_request.json
```

Get the key from the TypeSafe dashboard. Do not put it in source, prompts,
Discord, or the request body. `TYPESAFE_API_KEY` is also accepted for
upstream-compatible deployments.

For the official Python SDK workflow, install the declared dependency with
`python3 -m pip install -r infra/requirements.txt`. Runtime configuration lives
under `infra/`, including `infra/env/.env.example` and
`infra/pyproject.toml`. The bridge keeps a direct HTTP transport as its stable
runtime surface, matching the documented SDK request and response shapes and
keeping local verification dependency-free.

## Docker Compose

Compose wraps the existing CLI and the first real API surface. The API has one
health endpoint and one evaluation endpoint. No background workers are added.

```bash
export JEV_API_KEY='...'
docker compose -f infra/docker/compose.yml build
docker compose -f infra/docker/compose.yml run --rm jev-cli \
  < examples/basic_request.json
```

Run the API:

```bash
docker compose -f infra/docker/compose.yml up jev-api
curl http://localhost:8787/healthz
curl -X POST http://localhost:8787/v1/evaluate \
  -H 'Content-Type: application/json' \
  --data @examples/basic_request.json
```

The compose service passes `JEV_API_KEY`, `TYPESAFE_API_KEY`, and the optional
`TYPESAFE_API_BASE_URL` into the container. Keep the actual key outside the
repo.

## Covered behavior

- Jev default model (`jev-latest`)
- string, object, or array state
- Choice, Score, and Noul questions in one request
- structured question instructions and criteria
- transient-error retries with exponential backoff and `Retry-After`
- input validation and pass-through of typed answers, confidence,
  probabilities, model, and usage

## Verification

```bash
python3 -m unittest -v tests/integration/test_jev_client.py
```

The test uses a local mock server, including a 429 retry, so it does not need
an API key or contact TypeSafe.

The OpenClaw agent/tool registration step is intentionally not performed here:
that requires changing OpenClaw runtime configuration and the exact key delivery
method. The bridge is ready for registration once those are explicitly approved.
