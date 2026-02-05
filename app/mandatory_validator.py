from typing import Dict, List
import json
import logging

logger = logging.getLogger("mandatory_validator")
logger.setLevel(logging.DEBUG)

def load_mandatory_rules(path: str) -> Dict:
    with open(path, "r") as f:
        return json.load(f)


def normalize(text: str) -> str:
    return text.strip().lower()


def validate_mandatory_fields(
    canonical: Dict,
    mandatory_rules: Dict
):
    logger.debug("Full canonical dict: %s", json.dumps(canonical, indent=2))  # Add this line right after the function starts
    missing_fields: List[str] = []

    identity = canonical.get("project_identity", {})
    sector = normalize(identity.get("sector", ""))
    activity = normalize(identity.get("activity", ""))

    logger.debug("Validator | sector=%s activity=%s", sector, activity)
    logger.debug("Validator | canonical keys=%s", list(canonical.keys()))

    # 1️⃣ Global mandatory fields
    for field in mandatory_rules.get("global", []):
        if not _field_present(canonical, field):
            logger.debug("Missing global field: %s", field)
            missing_fields.append(field)

    # 2️⃣ Sector-level common fields
    sector_rules = mandatory_rules.get("sector", {}).get(sector, {})
    for field in sector_rules.get("common", []):
        if not _field_present(canonical, field):
            logger.debug("Missing sector-level common field: %s", field)
            missing_fields.append(field)

    # 3️⃣ Activity-level fields
    activity_rules = sector_rules.get("activities", {})
    matched_activity = None
    for activity_key in activity_rules.keys():
        if normalize(activity_key) == activity:
            matched_activity = activity_key
            break

    if matched_activity:
        required_fields = activity_rules.get(matched_activity, [])
        logger.debug("Validator | required_fields for activity '%s': %s", matched_activity, required_fields)

        for field in required_fields:
            if not _field_present(canonical, field):
                logger.debug("Missing activity-level field: %s", field)
                missing_fields.append(field)

    # 🔹 Deduplicate
    missing_fields = list(set(missing_fields))
    logger.debug("Final missing_fields: %s", missing_fields)

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
    # Check top-level first
    if field_name in canonical and canonical[field_name] not in ("", None):
        return True
    # Check derived_parameters
    derived = canonical.get("derived_parameters", {})
    if field_name in derived and derived[field_name] not in ("", None):
        return True
    
    def recursive_search(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == field_name:
                    print(f"DEBUG: Found field '{field_name}' with value: {v}")  # Temp
                    if v not in ("", None):
                        return True
                if recursive_search(v):
                    return True
        elif isinstance(obj, list):
            for item in obj:
                if recursive_search(item):
                    return True
        return False
    
    result = recursive_search(canonical)
    if not result:
        print(f"DEBUG: Field '{field_name}' NOT found in canonical")  # Temp
    return result