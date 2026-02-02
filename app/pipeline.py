import json
from app.field_mapper import map_fields_to_canonical, load_field_mapping
from app.mandatory_validator import validate_mandatory_fields
from app.override_evaluator import evaluate_overrides
from app.capacity_normalizer import normalize_capacity
from app.rule_engine import classify_by_rules

CATEGORY_AUTHORITY_MAP = {
    "A": {
        "clearance_authority": "MoEFCC",
        "appraisal_body": "EAC"
    },
    "B1": {
        "clearance_authority": "SEIAA",
        "appraisal_body": "SEAC"
    },
    "B2": {
        "clearance_authority": "DEIAA",
        "appraisal_body": "DEAC"
    }
}



class ClassificationPipeline:

    def __init__(self, config_dir: str):
        self.field_mapping = json.load(open(f"{config_dir}/field_mapping.json"))
        self.mandatory_rules = json.load(open(f"{config_dir}/mandatory_fields.json"))
        self.override_rules = json.load(open(f"{config_dir}/override_rules.json"))
        self.dss_rules = json.load(open(f"{config_dir}/dss_rules.json"))

    def run(self, raw_input: dict, debug: bool = False) -> dict:

        # STEP 1: Field Mapping
        canonical = map_fields_to_canonical(raw_input, self.field_mapping)

        # STEP 2: Override Evaluation (can run early)
        override = evaluate_overrides(canonical, self.override_rules)
        if override:
            return self._final_response(override, canonical, debug)

        # STEP 3: Capacity Normalization
        canonical = normalize_capacity(canonical)

        # STEP 4: Derived Parameters
        canonical.setdefault("derived_parameters", {})
        cap = canonical.get("capacity_normalization", {}).get("total_effective_capacity")
        if cap:
            canonical["derived_parameters"]["effective_capacity"] = cap["value"]

        # STEP 5: Mandatory Validation (AFTER derivation)
        validation = validate_mandatory_fields(canonical, self.mandatory_rules)
        if validation["status"] == "UNDETERMINED":
            return validation

        # STEP 6: DSS Rule Engine
        result = classify_by_rules(canonical, self.dss_rules)

        return self._final_response(result, canonical, debug)


    def _final_response(self, result: dict, canonical: dict, debug: bool):
        category = result.get("category")
        
        authority_info = CATEGORY_AUTHORITY_MAP.get(category, {})
        
        response = {
            "status": "CLASSIFIED",
            **result,
            **authority_info
        }
        
        # 🔽 STEP 2: Reduce confidence if semantic similarity was used
        derived = canonical.get("derived_parameters", {})
        if derived.get("activity_matched_by") == "semantic_similarity":
            original_conf = response.get("confidence", 1.0)
            response["confidence"] = min(original_conf, 0.85)
            
        if debug:
            response["canonical_project"] = canonical
        return response
