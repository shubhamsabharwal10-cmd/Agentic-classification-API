import json
from app.field_mapper import map_fields_to_canonical
from app.mandatory_validator import validate_mandatory_fields
from app.override_evaluator import evaluate_overrides
from app.capacity_normalizer import normalize_capacity
from app.rule_engine import classify_by_rules

CATEGORY_AUTHORITY_MAP = {
    "A": {"clearance_authority": "MoEFCC", "appraisal_body": "EAC"},
    "B1": {"clearance_authority": "SEIAA", "appraisal_body": "SEAC"},
    "B2": {"clearance_authority": "DEIAA", "appraisal_body": "DEAC"}
}

class ClassificationPipeline:

    def __init__(self, config_dir):
        self.field_mapping = json.load(open("{0}/field_mapping.json".format(config_dir)))
        self.mandatory_rules = json.load(open("{0}/mandatory_fields.json".format(config_dir)))
        self.override_rules = json.load(open("{0}/override_rules.json".format(config_dir)))
        self.dss_rules = json.load(open("{0}/dss_rules.json".format(config_dir)))

    def run(self, raw_input, debug=False):

        # STEP 1: Field Mapping
        canonical = map_fields_to_canonical(raw_input, self.field_mapping)

        # STEP 2: Override Evaluation
        override = evaluate_overrides(canonical, self.override_rules)
        if override:
            return self._final_response(override, canonical, debug)

        # STEP 3: Capacity Normalization (skips paper mill)
        canonical = normalize_capacity(canonical)

        # STEP 4: Derived Parameters
        canonical.setdefault("derived_parameters", {})
        
        # Special handling for paper mill (uses TPD not MTPA)
        identity = canonical.get("project_identity", {})
        activity = identity.get("activity", "").lower()
        cap_norm = canonical.get("capacity_normalization", {})
        
        if activity == "paper mill":
            # Paper mill: map proposed_capacity directly (already in TPD)
            # Note: Field mapper already moved it to capacity_normalization
            if "proposed_capacity" in cap_norm:
                canonical["derived_parameters"]["effective_capacity"] = cap_norm["proposed_capacity"]
        else:
            # Normal industry capacity mapping (MTPA)
            cap = cap_norm.get("total_effective_capacity")
            if cap:
                canonical["derived_parameters"]["effective_capacity"] = cap["value"]


        # Generic field mapping: Copy ALL numeric fields from form1_part_a to derived_parameters
        # This makes it future-proof for any new activities/fields
        form1 = canonical.get("form1_part_a", {})
        derived = canonical.get("derived_parameters", {})

        for field, value in form1.items():
            # Only copy numeric fields (int, float) to derived_parameters
            if isinstance(value, (int, float)) and field not in derived:
                canonical["derived_parameters"][field] = float(value)
                # Also copy to top-level for backward compatibility
                canonical[field] = float(value)


         # Debug: show canonical just before mandatory validation
        if debug:
            print("DEBUG canonical BEFORE mandatory validation:")
            print(json.dumps(canonical, indent=2))
            
        # STEP 5: Mandatory Validation
        validation = validate_mandatory_fields(canonical, self.mandatory_rules)
        if validation["status"] == "UNDETERMINED":
            return validation

        # DEBUG
        if debug:
            print("DEBUG canonical BEFORE rule engine:")
            print(json.dumps(canonical, indent=2))

        # STEP 6: DSS Rule Engine
        result = classify_by_rules(canonical, self.dss_rules)
        return self._final_response(result, canonical, debug)

    def _final_response(self, result, canonical, debug):
        category = result.get("category")
        authority_info = CATEGORY_AUTHORITY_MAP.get(category, {})
        response = {
            "status": "CLASSIFIED",
            **result,
            **authority_info
        }
        derived = canonical.get("derived_parameters", {})
        if derived.get("activity_matched_by") == "semantic_similarity":
           response["confidence"] = min(response.get("confidence", 1.0), 0.85)
        if debug:
            response["canonical_project"] = canonical
        return response
