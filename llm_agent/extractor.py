import json
from llm_agent.schemas import RawProjectInput
from llm_agent.bedrock_client import BedrockClient
import llm_agent.schemas
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
    "sand mining": "sand mining"
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
    "proposed_capacity": {
        "value": "number",
        "unit": "string"
    },
    "existing_capacity": {
        "value": "number",
        "unit": "string"
    },
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
- For capacity fields, ALWAYS output value in MTPA
- Unit must be "MTPA"



ACTIVITY NORMALIZATION RULES:
- "cement plant", "cement factory" → project_activity = "cement"
- "steel plant", "steel factory" → project_activity = "steel plant"
- "thermal power plant", "thermal plant" → project_activity = "thermal power plant"
- "sugar mill", "sugar factory" → project_activity = "sugar industry"
- "highway", "road project" → project_activity = "highway project"
- "building", "construction" → project_activity = "construction project"
- "hydro project", "hydroelectric" → project_activity = "hydroelectric project"

"""

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

User input:
\"\"\"{user_text}\"\"\"

JSON output:
"""
        raw_output = self.llm.invoke(prompt)

        try:
            parsed = json.loads(raw_output)
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
            
            # # ✅ ADD THIS BLOCK
            # form1 = parsed.setdefault("form1_part_a", {})
            # if "proposed_capacity" in form1 and isinstance(form1["proposed_capacity"], (int, float)):
            #     form1["proposed_capacity"] = {
            #         "value": form1["proposed_capacity"],
            #         "unit": "MTPA"
            #     }
            
            # 🔑 GENERIC FLATTENING OF LLM NUMERIC OBJECTS
            # 🔑 SAFE FLATTENING (exclude DSS semantic fields)
            # DO_NOT_FLATTEN = {
            #     "proposed_capacity",
            #     "existing_capacity"
            # }
            # NUMERIC_CONTAINERS = [
            #     "form1_part_a",
            #     "environmental_sensitivity"
            # ]

            # for container in NUMERIC_CONTAINERS:
            #     block = parsed.get(container, {})
            #     if not isinstance(block, dict):
            #         continue

            #     for key, value in list(block.items()):
            #         if key in DO_NOT_FLATTEN:
            #             continue
                    
            #         if isinstance(value, dict) and "value" in value:
            #             if isinstance(value["value"], (int, float)):
            #                 block[key] = value["value"]

                
            RawProjectInput(**parsed)  # validation
            return parsed
        except Exception as e:
            raise ValueError(f"Invalid LLM output: {e}")
