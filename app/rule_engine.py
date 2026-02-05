from typing import Dict
from app.activity_similarity import ActivitySimilarityEngine
import logging

METRIC_SEMANTICS = {
    "capacity": {"effective_capacity", "proposed_capacity", "existing_capacity", "power_generation_mw", "hydro_capacity_mw"},
    "absolute": {"sand_extraction_m3_per_year", "coal_production_mtpA", "minor_mineral_area_ha", "max_mining_area_ha", "road_length_km", "built_up_area_sqm", "dam_height_m", "sugar_crushing_tcd"}
}

logger = logging.getLogger("dss.semantic_similarity")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)

SIMILARITY_THRESHOLD = 0.85
_similarity_engines = {}

def classify_by_rules(canonical: Dict, dss_rules: Dict) -> Dict:
    identity = canonical.get("project_identity", {})
    sector = identity.get("sector", "").lower()
    activity = identity.get("activity", "").lower()

    sector_rules = dss_rules.get(sector)
    if not sector_rules:
        return _fallback()

    # STEP 1: Exact match rules
    for activity_key, rules in sector_rules.items():
        if activity_key == activity:
            for rule in rules:
                if "condition" not in rule:
                    return _result(rule)
                if _evaluate_condition(rule["condition"], canonical):
                    return _result(rule)

    # STEP 2: Semantic fallback
    if activity:
        if sector not in _similarity_engines:
            _similarity_engines[sector] = ActivitySimilarityEngine(sector_rules.keys())
        engine = _similarity_engines[sector]
        closest, score = engine.find_closest(activity)
        if score >= SIMILARITY_THRESHOLD and closest != activity and not canonical.get('_similarity_used', False):  # Fixed: Prevent infinite loop
            canonical['_similarity_used'] = True
            canonical["derived_parameters"]["activity_matched_by"] = "semantic_similarity"
            canonical["derived_parameters"]["similarity_score"] = score
            identity["activity"] = closest
            return classify_by_rules(canonical, dss_rules)

    return _fallback()

def _evaluate_condition(condition: dict, canonical: dict) -> bool:
    if "any" in condition:
        return any(_evaluate_condition(c, canonical) for c in condition["any"] if isinstance(c, dict))

    field = condition.get("field")
    if not field:
        return False

    value = _resolve_field_value(canonical, field)
    if value is None:
        return False

    try:
        value = float(value) if not isinstance(value, dict) else float(value.get("value", value))
        threshold = float(condition.get("value"))
    except (TypeError, ValueError):
        return False

    op = condition.get("op")
    if op == ">=":
        return value >= threshold
    if op == ">":
        return value > threshold
    if op == "<=":
        return value <= threshold
    if op == "<":
        return value < threshold
    if op == "==":
        return value == threshold
    return False

def _resolve_field_value(canonical: Dict, field: str):
    # Check derived_parameters first
    derived = canonical.get("derived_parameters", {})
    if field in derived and derived[field] is not None:
        val = derived[field]
        return float(val["value"]) if isinstance(val, dict) and "value" in val else float(val)

    # Then check form1_part_a
    form1 = canonical.get("form1_part_a", {})
    if field in form1 and form1[field] is not None:
        val = form1[field]
        return float(val["value"]) if isinstance(val, dict) and "value" in val else float(val)

    # Capacity normalization
    if field in METRIC_SEMANTICS.get("capacity", set()):
        cap_block = canonical.get("capacity_normalization", {}).get("total_effective_capacity", {})
        if "value" in cap_block:
            return float(cap_block["value"])

    # Absolute metrics
    if field in METRIC_SEMANTICS.get("absolute", set()):
        for source in [derived, form1, canonical]:
            if field in source:
                val = source[field]
                return float(val) if not isinstance(val, dict) else float(val.get("value", val))

    # Fallback
    if field in canonical:
        val = canonical[field]
        return float(val) if not isinstance(val, dict) else float(val.get("value", val))
    return None

def _result(rule: Dict) -> Dict:
    return {"category": rule["category"], "decision_mode": "RULE_BASED", "triggered_rule": rule.get("reason", "Rule matched"), "confidence": 0.95 if rule["category"] != "B2" else 0.9}

def _fallback() -> Dict:
    return {"category": "B2", "decision_mode": "DEFAULT_FALLBACK", "triggered_rule": "No matching DSS rule", "confidence": 0.6}
