from typing import Dict, Optional


def normalize_capacity(canonical: dict) -> dict:
    identity = canonical.get("project_identity", {})
    sector = identity.get("sector", "").lower()
    activity = identity.get("activity", "").lower()
    proposal_type = identity.get("type_of_proposal", "").lower()

    # 🚫 Infrastructure projects do not use capacity normalization
    if sector != "industry":
        return canonical
    
    # 🚫 Paper mill uses TPD (tons per day) not MTPA - skip normalization
    if activity == "paper mill":
        return canonical

    # 🔑 Normalize proposal semantics
    if proposal_type == "greenfield":
        proposal_type = "new"
        identity["type_of_proposal"] = "new"

    form1 = canonical.get("form1_part_a", {})
    cap_block = canonical.setdefault("capacity_normalization", {})

    # 🔑 Normalize proposed capacity (form1 → capacity_normalization)
    if "proposed_capacity" in form1 and "proposed_capacity" not in cap_block:
        value = form1.get("proposed_capacity")
        if isinstance(value, dict) and "value" in value:  # Fixed: Handle dict
            value = value["value"]
        if isinstance(value, (int, float)):
            cap_block["proposed_capacity"] = {
                "value": value,
                "unit": "MTPA"
            }

    # 🔑 Normalize existing capacity (same fix)
    if "existing_capacity" in form1 and "existing_capacity" not in cap_block:
        value = form1.get("existing_capacity")
        if isinstance(value, dict) and "value" in value:
            value = value["value"]
        if isinstance(value, (int, float)):
            cap_block["existing_capacity"] = {
                "value": value,
                "unit": "MTPA"
            }
            
    # Ensure cap_block values are dicts (force conversion if needed)
    for key in ["proposed_capacity", "existing_capacity"]:
        if key in cap_block and not isinstance(cap_block[key], dict):
            value = cap_block[key]
            if isinstance(value, (int, float)):
                cap_block[key] = {"value": value, "unit": "MTPA"}

    existing = cap_block.get("existing_capacity")
    proposed = cap_block.get("proposed_capacity")

    total_capacity = None

    if proposal_type == "expansion":
        if existing and proposed:
            total_capacity = {
                "value": (existing.get("value", 0) or 0) + (proposed.get("value", 0) or 0),
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


