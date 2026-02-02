from typing import Dict, Any
import json


def load_field_mapping(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


def get_nested_value(data: Dict, path: str):
    """
    Safely extract value from nested dict using dot path.
    Example: 'form1_part_a.q_1_2'
    """
    keys = path.split(".")
    current = data

    for key in keys:
        if not isinstance(current, dict):
            return None
        if key not in current:
            return None
        current = current[key]

    if current in ("", None):
        return None

    return current


def set_nested_value(target: Dict, path: str, value: Any):
    """
    Set value in nested dict using dot path.
    """
    keys = path.split(".")
    current = target

    for key in keys[:-1]:
        current = current.setdefault(key, {})

    current[keys[-1]] = value


def map_fields_to_canonical(
    raw_input: Dict,
    field_mapping: Dict
):
    canonical = {
        "project_identity": {},
        "validation_status": {
            "missing_mandatory_fields": [],
            "is_valid_for_classification": True
        }
    }

    for field_name, config in field_mapping.items():
        found = False

        for source_path in config["sources"]:
            value = get_nested_value(raw_input, source_path)
            if value is not None:
                set_nested_value(
                    canonical,
                    config["canonical_path"],
                    value
                )
                found = True
                break

        if not found:
            canonical["validation_status"]["missing_mandatory_fields"].append(field_name)

    if canonical["validation_status"]["missing_mandatory_fields"]:
        canonical["validation_status"]["is_valid_for_classification"] = False

    return canonical
