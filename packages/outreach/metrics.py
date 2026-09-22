"""Calibration and drift calculations for persisted outreach scores."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from .audit import POSITIVE_OUTCOMES

ACTIONABLE = {"draft_for_review", "human_review"}
SIGNALS = ("icp_fit", "buyer_relevance", "buying_signal", "personalization_evidence")


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def classification_metrics(rows: list[dict[str, Any]], minimum_labeled: int) -> dict[str, Any]:
    labeled = len(rows)
    actual_positive = sum(row["outcome"] in POSITIVE_OUTCOMES for row in rows)
    predicted_positive = sum(row["action"] in ACTIONABLE for row in rows)
    true_positive = sum(
        row["action"] in ACTIONABLE and row["outcome"] in POSITIVE_OUTCOMES for row in rows
    )
    false_positive = predicted_positive - true_positive
    false_negative = actual_positive - true_positive
    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    f1 = _ratio(2 * precision * recall, precision + recall) if precision is not None and recall is not None and precision + recall else None
    groups: dict[str, dict[str, int]] = {}
    for row in rows:
        groups.setdefault(row["action"], {})[row["outcome"]] = groups.setdefault(row["action"], {}).get(row["outcome"], 0) + 1
    by_action = {}
    for action, outcomes in groups.items():
        count = sum(outcomes.values())
        positive = sum(value for outcome, value in outcomes.items() if outcome in POSITIVE_OUTCOMES)
        by_action[action] = {
            "labeled": count,
            "positive": positive,
            "positive_rate": _ratio(positive, count),
            "status": "ready" if count >= minimum_labeled else "insufficient_data",
            "outcomes": outcomes,
        }
    return {
        "labeled": labeled,
        "actual_positive": actual_positive,
        "predicted_positive": predicted_positive,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "by_action": by_action,
        "status": "ready" if labeled >= minimum_labeled else "insufficient_data",
    }


def drift_report(rows: list[dict[str, Any]], recent_days: int = 7) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(days=recent_days)
    baseline_cutoff = now - timedelta(days=recent_days * 2)
    recent = [row for row in rows if row["created_at"] >= recent_cutoff]
    baseline = [row for row in rows if baseline_cutoff <= row["created_at"] < recent_cutoff]

    def distribution(items: list[dict[str, Any]], key: str) -> dict[str, float]:
        counts = Counter(item[key] for item in items)
        total = len(items)
        return {name: round(value / total, 4) for name, value in counts.items()} if total else {}

    def means(items: list[dict[str, Any]]) -> dict[str, float]:
        values = {}
        for signal in SIGNALS:
            numbers = [item["policy"].get("signals", {}).get(signal) for item in items]
            numbers = [value for value in numbers if isinstance(value, (int, float))]
            if numbers:
                values[signal] = round(sum(numbers) / len(numbers), 4)
        return values

    recent_means = means(recent)
    baseline_means = means(baseline)
    return {
        "recent_days": recent_days,
        "baseline_count": len(baseline),
        "recent_count": len(recent),
        "status": "ready" if baseline and recent else "insufficient_data",
        "baseline_actions": distribution(baseline, "action"),
        "recent_actions": distribution(recent, "action"),
        "baseline_confidence_bands": distribution(baseline, "confidence_band"),
        "recent_confidence_bands": distribution(recent, "confidence_band"),
        "baseline_signal_means": baseline_means,
        "recent_signal_means": recent_means,
        "signal_deltas": {
            signal: round(recent_means[signal] - baseline_means[signal], 4)
            for signal in recent_means.keys() & baseline_means.keys()
        },
    }
