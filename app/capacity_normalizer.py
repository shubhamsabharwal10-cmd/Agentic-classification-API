from typing import Dict, Optional


def normalize_capacity(canonical: dict) -> dict:
    identity = canonical.get("project_identity", {})
    sector = identity.get("sector", "").lower()
    proposal_type = identity.get("type_of_proposal", "").lower()

    # 🚫 Infrastructure projects do not use capacity normalization
    if sector == "infrastructure":
        return canonical

    cap_block = canonical.setdefault("capacity_normalization", {})

    existing = cap_block.get("existing_capacity")
    proposed = cap_block.get("proposed_capacity")

    total_capacity = None

    if proposal_type == "expansion":
        if existing and proposed:
            total_capacity = {
                "value": existing.get("value", 0) + proposed.get("value", 0),
                "unit": proposed.get("unit") or existing.get("unit") or "MTPA"
            }
        elif proposed:
            total_capacity = {
                "value": proposed.get("value"),
                "unit": proposed.get("unit") or "MTPA"
            }

    elif proposal_type == "new":
        if proposed:
            total_capacity = {
                "value": proposed.get("value"),
                "unit": proposed.get("unit") or "MTPA"
            }

    cap_block["total_effective_capacity"] = total_capacity

    return canonical

