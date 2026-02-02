from typing import Dict, Optional


def get_nested_value(data: Dict, path: str):
    keys = path.split(".")
    current = data

    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
        if current is None:
            return None
    return current


def evaluate_overrides(
    canonical: Dict,
    override_rules: Dict
) -> Optional[Dict]:
    """
    Returns override decision if triggered, else None
    """

    # 1. Absolute overrides
    for rule in override_rules.get("absolute_overrides", []):
        value = get_nested_value(canonical, rule["canonical_path"])

        if "trigger_value" in rule:
            if value == rule["trigger_value"]:
                return _override_result(rule["reason"])

        elif "trigger_condition" in rule and value is not None:
            cond = rule["trigger_condition"]
            if _evaluate_condition(value, cond):
                return _override_result(rule["reason"])

    # 2. Activity-based overrides
    activity = canonical.get("project_identity", {}).get("activity", "").lower()

    for rule in override_rules.get("activity_overrides", []):
        if rule["activity_contains"] in activity:
            return _override_result(rule["reason"])

    return None


def _evaluate_condition(value, condition: Dict) -> bool:
    op = condition["operator"]
    threshold = condition["value"]

    if op == ">":
        return value > threshold
    if op == ">=":
        return value >= threshold
    if op == "<":
        return value < threshold
    if op == "<=":
        return value <= threshold

    return False


def _override_result(reason: str) -> Dict:
    return {
        "override_triggered": True,
        "category": "A",
        "decision_mode": "OVERRIDE",
        "reason": reason,
        "confidence": 1.0
    }
