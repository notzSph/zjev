"""Approved discovery source adapters.

Google Places discovers companies, not verified buyers. Results therefore remain
research leads until a person, role, and activity are manually enriched.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable

GOOGLE_PLACES_URL = "https://places.googleapis.com/v1/places:searchText"


class SourceNotConfigured(RuntimeError):
    pass


def source_status() -> dict[str, dict[str, Any]]:
    import os

    return {
        "csv": {"available": True, "mode": "import", "requires_credentials": False},
        "google_places": {
            "available": bool(os.environ.get("GOOGLE_MAPS_API_KEY")),
            "mode": "company_discovery",
            "requires_credentials": True,
        },
        "zcrm": {
            "available": bool(os.environ.get("ZCRM_API_URL") and os.environ.get("ZCRM_API_TOKEN")),
            "mode": "crm_import",
            "requires_credentials": True,
        },
    }


def _lead(place: dict[str, Any]) -> dict[str, Any]:
    display_name = place.get("displayName") or {}
    name = display_name.get("text")
    address = place.get("formattedAddress") or ""
    maps_uri = place.get("googleMapsUri")
    if not isinstance(name, str) or not name.strip() or not isinstance(maps_uri, str):
        raise ValueError("Google Places result is missing a name or Maps URL")
    place_id = place.get("id") or name.strip()
    types = place.get("types") or []
    evidence = [f"Google Places result for {name.strip()}"]
    if address:
        evidence.append(f"Listed address: {address}")
    if types:
        evidence.append(f"Place types: {', '.join(str(item) for item in types)}")
    return {
        "candidate_id": f"google-place:{place_id}",
        "person_name": None,
        "company_name": name.strip(),
        "role": "unresolved buyer role",
        "geography": address or "unknown",
        "target_profile": f"Company discovered through Google Places: {name.strip()}",
        "linkedin_activity": "No activity supplied; manual enrichment required",
        "evidence": evidence,
        "source_urls": [maps_uri],
        "source_records": [{
            "url": maps_uri,
            "captured_at": None,
            "source_type": "google_places",
        }],
        "discovery_only": True,
    }


def search_google_places(
    api_key: str,
    query: str,
    *,
    max_results: int = 20,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> list[dict[str, Any]]:
    if not isinstance(api_key, str) or not api_key.strip():
        raise SourceNotConfigured("Google Places requires GOOGLE_MAPS_API_KEY")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if not isinstance(max_results, int) or not 1 <= max_results <= 20:
        raise ValueError("max_results must be between 1 and 20")
    payload = json.dumps({"textQuery": query.strip(), "pageSize": max_results}).encode()
    request = urllib.request.Request(
        GOOGLE_PLACES_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key.strip(),
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.googleMapsUri,places.types",
        },
        method="POST",
    )
    try:
        with opener(request, timeout=15) as response:
            body = json.loads(response.read())
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError("Google Places request failed") from error
    if not isinstance(body, dict) or not isinstance(body.get("places", []), list):
        raise RuntimeError("Google Places returned an invalid response")
    return [_lead(place) for place in body["places"] if isinstance(place, dict)]
