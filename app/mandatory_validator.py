from typing import Dict, List
import json


def load_mandatory_rules(path: str) -> Dict:
    with open(path, "r") as f:
        return json.load(f)


def normalize(text: str) -> str:
    return text.strip().lower()


def validate_mandatory_fields(
    canonical: Dict,
    mandatory_rules: Dict
):
    missing_fields: List[str] = []

    identity = canonical.get("project_identity", {})
    sector = normalize(identity.get("sector", ""))
    activity = normalize(identity.get("activity", ""))

    # 1. Global mandatory fields
    for field in mandatory_rules.get("global", []):
        if not _field_present(canonical, field):
            missing_fields.append(field)

    # 2. Sector-level mandatory fields
    sector_rules = mandatory_rules.get("sector", {}).get(sector, {})

    for field in sector_rules.get("common", []):
        if not _field_present(canonical, field):
            missing_fields.append(field)

    # 3. Activity-level mandatory fields (STRICT MATCH)
    activity_rules = sector_rules.get("activities", {})

    matched_activity = None
    for activity_key in activity_rules.keys():
        if normalize(activity_key) == activity:
            matched_activity = activity_key
            break

    if matched_activity:
        required_fields = activity_rules.get(matched_activity, [])

        # 🔑 SPECIAL CASE: Hydroelectric Project (OR-mandatory)
        if normalize(matched_activity) == "hydroelectric project":
            has_capacity = _field_present(canonical, "hydro_capacity_mw")
            has_height = _field_present(canonical, "dam_height_m")

            if not (has_capacity or has_height):
                missing_fields.extend(["hydro_capacity_mw", "dam_height_m"])

        # 🔒 DEFAULT: all other activities (AND-mandatory)
        else:
            for field in required_fields:
                if not _field_present(canonical, field):
                    missing_fields.append(field)

    # Deduplicate
    missing_fields = list(set(missing_fields))

    if missing_fields:
        return {
            "status": "UNDETERMINED",
            "reason": "Missing mandatory fields",
            "missing_fields": missing_fields
        }

    return {
        "status": "VALID",
        "missing_fields": []
    }


def _field_present(canonical: Dict, field_name: str) -> bool:
    """
    Checks if a field exists anywhere in canonical object.
    """
    def recursive_search(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == field_name and v not in ("", None):
                    return True
                if recursive_search(v):
                    return True
        elif isinstance(obj, list):
            for item in obj:
                if recursive_search(item):
                    return True
        return False

    return recursive_search(canonical)
