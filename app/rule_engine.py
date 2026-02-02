from typing import Dict, Any, Optional
from app.activity_similarity import ActivitySimilarityEngine

import logging

logger = logging.getLogger("dss.semantic_similarity")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )
    handler.setFormatter(formatter)
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

    for activity_key, rules in sector_rules.items():
        if activity_key in activity:
            for rule in rules:
                # Rule without condition → default match
                if "condition" not in rule:
                    return _result(rule)

                if _evaluate_condition(rule["condition"], canonical):
                    return _result(rule)
                
    # 2️⃣ STEP 4B — Semantic fallback (NEW)
    if activity:
        if sector not in _similarity_engines:
            _similarity_engines[sector] = ActivitySimilarityEngine(sector_rules.keys())

        engine = _similarity_engines[sector]
        closest, score = engine.find_closest(activity)

        if score >= SIMILARITY_THRESHOLD and closest != activity:
            logger.info(
                "Semantic activity match used | sector=%s | original_activity='%s' | "
                "matched_activity='%s' | similarity_score=%.3f",
                sector,
                activity,
                closest,
                score
            )
            
            # ✅ ADD THESE 3 LINES (RIGHT HERE)
            canonical.setdefault("derived_parameters", {})
            canonical["derived_parameters"]["activity_matched_by"] = "semantic_similarity"
            canonical["derived_parameters"]["similarity_score"] = score
            
            # rewrite activity & retry exact match
            identity["activity"] = closest
            return classify_by_rules(canonical, dss_rules)

    return _fallback()


def _evaluate_condition(condition: Dict, canonical: Dict) -> bool:
    """
    Safely evaluate a rule condition against the canonical object.
    """

    # OR conditions
    if "any" in condition:
        return any(_evaluate_condition(c, canonical) for c in condition["any"])

    field = condition["field"]
    value = _resolve_field_value(canonical, field)

    if value is None:
        return False

    op = condition["op"]
    threshold = condition["value"]

    try:
        if op == ">=":
            return value >= threshold
        if op == ">":
            return value > threshold
        if op == "<":
            return value < threshold
        if op == "<=":
            return value <= threshold
        if op == "==":
            return value == threshold

    except TypeError:
        # Defensive: mismatched types should never crash DSS
        return False

    return False


def _resolve_field_value(canonical: Dict, field: str) -> Optional[Any]:
    """
    Resolve a field value from the canonical object in a sector-safe way.
    """

    # 1️⃣ Derived parameters (mining, infrastructure, misc)
    derived = canonical.get("derived_parameters", {})
    if field in derived:
        return derived.get(field)

    # 2️⃣ Effective capacity (industry rules)
    if field == "effective_capacity":
        return (
            canonical
            .get("capacity_normalization", {})
            .get("total_effective_capacity", {})
            .get("value")
        )

    # 3️⃣ Fallback: direct canonical lookup (rare cases)
    return canonical.get(field)


def _result(rule: Dict) -> Dict:
    return {
        "category": rule["category"],
        "decision_mode": "RULE_BASED",
        "triggered_rule": rule.get("reason", "Rule matched"),
        "confidence": 0.95 if rule["category"] != "B2" else 0.9
    }


def _fallback() -> Dict:
    return {
        "category": "B2",
        "decision_mode": "DEFAULT_FALLBACK",
        "triggered_rule": "No matching DSS rule",
        "confidence": 0.6
    }
