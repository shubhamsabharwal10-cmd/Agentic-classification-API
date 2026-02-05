import logging

import json
from venv import logger
from llm_agent.schemas import RawProjectInput
from llm_agent.bedrock_client import BedrockClient
import llm_agent.schemas

logger = logging.getLogger(__name__)

print("USING SCHEMAS FROM:", llm_agent.schemas.__file__)


ACTIVITY_KEYWORDS = {
    "cement": "cement",
    "cement plant": "cement",
    "cement factory": "cement",

    "steel plant": "steel plant",
    "steel factory": "steel plant",

    "thermal power plant": "thermal power plant",
    "thermal plant": "thermal power plant",

    "sugar industry": "sugar industry",
    "sugar mill": "sugar industry",
    "sugar factory": "sugar industry",

    "highway": "highway project",
    "road project": "highway project",

    "construction": "construction project",
    "building project": "construction project",

    "hydroelectric": "hydroelectric project",
    "hydro project": "hydroelectric project",

    "iron ore": "iron ore",
    "coal mining": "coal mining",
    "sand mining": "sand mining",
    "limestone mining": "limestone mining",
    "limestone quarry": "limestone mining",

    "paper mill": "paper mill",
    "paper factory": "paper mill",
    "paper manufacturing": "paper mill"
}

# Map activities to their sectors
ACTIVITY_TO_SECTOR = {
    "cement": "industry",
    "steel plant": "industry",
    "thermal power plant": "industry",
    "sugar industry": "industry",
    "paper mill": "industry",
    
    "coal mining": "mining",
    "iron ore": "mining",
    "sand mining": "mining",
    "limestone mining": "mining",
    
    "highway project": "infrastructure",
    "construction project": "infrastructure",
    "hydroelectric project": "infrastructure"
}

ACTIVITY_CAPACITY_FIELD_MAP = {
    # Industry
    "cement": "proposed_capacity",
    "steel plant": "proposed_capacity",

    # Mining
    "coal mining": "coal_production_mtpA",
    "iron ore": "max_mining_area_ha",
    "sand mining": "sand_extraction_m3_per_year",
    "limestone mining": "max_mining_area_ha",

    # Industry
    "paper mill": "proposed_capacity",

    # Power / Infra
    "thermal power plant": "power_generation_mw",
    "hydroelectric project": "hydro_capacity_mw"
}

SYSTEM_PROMPT = """
You are an information extraction engine.

You MUST output JSON that strictly follows THIS schema.
DO NOT invent new keys.
DO NOT rename keys.
DO NOT nest fields incorrectly.

ALLOWED STRUCTURE ONLY:

{
  "caf": {
    "project_sector": "string",
    "type_of_proposal": "string",
    "state": "string",
    "district": "string"
  },
  "form1_part_a": {
    "project_activity": "string",
    "proposed_capacity": "number",
    "existing_capacity": "number",
    "max_mining_area_ha": "number",
    "coal_production_mtpA": "number",
    "sand_extraction_m3_per_year": "number",
    "minor_mineral_area_ha": "number",
    "power_generation_mw": "number",
    "road_length_km": "number",
    "built_up_area_sqm": "number",
    "hydro_capacity_mw": "number",
    "dam_height_m": "number",
    "port_type": "string",
    "airport_type": "string",
    "expansion_type": "string"
  },
  "environmental_sensitivity": {
    "protected_area_within_10km": "boolean",
    "forest_land_area_ha": "number",
    "crz_applicable": "boolean",
    "general_condition_applicable": "boolean"
  }
}

RULES:
- Use ONLY the keys shown above
- If information is missing, OMIT the key
- Do NOT create keys like project_type, project_location, project_capacity
- Sector must be one of: mining, industry, infrastructure
- Output VALID JSON only
- For cement, steel, sugar: capacity in MTPA
- For paper mill: capacity in TPD (tons per day), output the numeric value directly
- For mining: area in hectares, production as specified



ACTIVITY NORMALIZATION RULES:
- "cement plant", "cement factory" → project_activity = "cement"
- "steel plant", "steel factory" → project_activity = "steel plant"
- "thermal power plant", "thermal plant" → project_activity = "thermal power plant"
- "sugar mill", "sugar factory" → project_activity = "sugar industry"
- "paper mill", "paper factory", "paper manufacturing" → project_activity = "paper mill"
- "limestone mining", "limestone quarry" → project_activity = "limestone mining"
- "highway", "road project" → project_activity = "highway project"
- "building", "construction" → project_activity = "construction project"
- "hydro project", "hydroelectric" → project_activity = "hydroelectric project"

"""

def _flatten_numeric_objects(obj):
    """
    Recursively flatten dicts like {"value": x, "unit": "..."} → x,
    but only for fields where canonical unit matches industrial capacities.
    """
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if isinstance(v, dict) and "value" in v and isinstance(v["value"], (int, float)):
                # Only flatten industrial capacities, skip mining/other units
                if k in ("proposed_capacity", "existing_capacity", "power_generation_mw", "hydro_capacity_mw"):
                    obj[k] = v["value"]
            else:
                _flatten_numeric_objects(v)
    elif isinstance(obj, list):
        for item in obj:
            _flatten_numeric_objects(item)



def remove_empty_values(obj):
    if isinstance(obj, dict):
        return {
            k: remove_empty_values(v)
            for k, v in obj.items()
            if v not in ("", None)
        }
    return obj


class FieldExtractor:
    def __init__(self):
        self.llm = BedrockClient()

    def extract(self, user_text: str) -> dict:
        prompt = f"""
{SYSTEM_PROMPT}

Examples:
- "Coal mining with 10 MTPA production" → {{"form1_part_a": {{"project_activity": "coal mining", "coal_production_mtpA": 10}}}}
- "Cement plant 2 MTPA" → {{"form1_part_a": {{"project_activity": "cement", "proposed_capacity": 2}}}}
- "Paper mill 300 TPD" → {{"form1_part_a": {{"project_activity": "paper mill", "proposed_capacity": 300}}}}
- "Limestone mining 80 hectares" → {{"form1_part_a": {{"project_activity": "limestone mining", "max_mining_area_ha": 80}}}}


User input:\"{user_text}\"

JSON output:
"""
        raw_output = self.llm.invoke(prompt)

        try:
            parsed = json.loads(raw_output)
        except json.JSONDecodeError as e:
            logger.error("LLM output invalid JSON: %s", raw_output)
            parsed = {}  # Fallback
            
        parsed = remove_empty_values(parsed)
            
        text = user_text.lower()
        for keyword, activity in ACTIVITY_KEYWORDS.items():
            if keyword in text:
                parsed.setdefault("form1_part_a", {})["project_activity"] = activity
                self.last_activity = activity
                break
        parsed.setdefault("form1_part_a", {}).setdefault(
            "project_activity",
            getattr(self, "last_activity", None)
        )
        
        # 🔑 Auto-populate sector based on activity
        activity = parsed.get("form1_part_a", {}).get("project_activity")
        if activity and activity in ACTIVITY_TO_SECTOR:
            parsed.setdefault("caf", {})["project_sector"] = ACTIVITY_TO_SECTOR[activity]
            
        _flatten_numeric_objects(parsed)

            
        # 🔑 Activity-aware capacity remapping (GENERIC)
        form1 = parsed.get("form1_part_a", {})
        activity = form1.get("project_activity")

        if activity in ACTIVITY_CAPACITY_FIELD_MAP:
            target_field = ACTIVITY_CAPACITY_FIELD_MAP[activity]

            # If generic proposed_capacity exists but activity expects a different field
            if (
                "proposed_capacity" in form1
                and target_field not in form1
                and isinstance(form1["proposed_capacity"], (int, float))
            ):
                form1[target_field] = form1["proposed_capacity"]
                del form1["proposed_capacity"]

        try:    
            RawProjectInput(**parsed)  # validation
            return parsed
        except Exception as e:
            logger.error("Validation failed: %s", e)
            return {}  # Fallback
