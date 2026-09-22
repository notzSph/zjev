"""Explicit working calibration for z's current acquisition motion.

This is configuration, not learned truth. It is intentionally visible so it can
be changed when the offer, geography, or measured funnel changes.
"""

Z_CALIBRATION_VERSION = "2026-09-22.v1"

ICP = {
    "geography": ["Piedmont", "Italy"],
    "company_profile": "SMBs with a concrete operational or digital workflow problem",
    "buyer_titles": ["CEO", "CTO", "COO", "digital lead", "innovation lead"],
    "priority_signals": [
        "manual or fragmented business workflow",
        "active software, AI, automation, or integration initiative",
        "visible operational bottleneck or growth pressure",
        "recent post or event showing a relevant problem",
    ],
}

OFFER_LANES = [
    "custom software systems",
    "AI and workflow automation",
    "data, research, and information pipelines",
    "systems integration and operational tooling",
]

OPERATING_RULES = {
    "sequence": ["connection_request", "follow_up", "qualification", "call"],
    "volume": "low-volume and manual",
    "human_approval_required": True,
    "auto_send": False,
    "do_not_use": [
        "generic flattery",
        "invented familiarity or pain",
        "unsupported ROI or capability claims",
        "mass or automated LinkedIn behavior",
    ],
}

DISQUALIFIERS = [
    "no defensible relevance to an offer lane",
    "no credible buyer or influencer relevance",
    "no evidence for a specific opening angle",
    "unsupported claim risk that cannot be removed",
    "outreach would require high-volume or automated behavior",
]
