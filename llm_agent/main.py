import re
import json
from fastapi import FastAPI
import requests

from llm_agent.extractor import FieldExtractor
from llm_agent.conversation import ConversationState

# ------------------ CAF Fallback ------------------
def extract_caf_fields(text: str) -> dict:
    """
    Generic fallback for CAF fields if not extracted by LLM.
    """
    caf = {}
    text_lower = text.lower()

    # Match state
    state_match = re.search(r"in\s+([a-z\s]+?)[\.\,]?$", text_lower)
    if state_match:
        caf["state"] = state_match.group(1).title()

    # Match district
    district_match = re.search(r"(\b[a-z\s]+?)\s+district", text_lower)
    if district_match:
        caf["district"] = district_match.group(1).title()

    # Default type_of_proposal
    caf["type_of_proposal"] = "new"

    # Infer sector generically from keywords
    if "hydro" in text_lower or "hydroelectric" in text_lower:
        caf["project_sector"] = "infrastructure"
    elif "construction" in text_lower or "building" in text_lower or "highway" in text_lower:
        caf["project_sector"] = "infrastructure"
    elif "coal" in text_lower or "iron ore" in text_lower or "sand" in text_lower:
        caf["project_sector"] = "mining"
    elif "cement" in text_lower or "steel" in text_lower or "thermal power" in text_lower or "sugar" in text_lower:
        caf["project_sector"] = "industry"

    return caf


# ------------------ DSS API ------------------
DSS_API_URL = "http://127.0.0.1:8000/classify"

app = FastAPI(title="Parivesh LLM Agent")
extractor = FieldExtractor()
conversation = ConversationState()


# ------------------ Numeric Patterns (Flexible Units) ------------------
NUMERIC_PATTERNS = {
    "proposed_capacity": {"units": ["mtpa"], "keywords": ["capacity", "production", "plant capacity"]},
    "existing_capacity": {"units": ["mtpa"], "keywords": ["existing capacity"]},
    "power_generation_mw": {"units": ["mw"], "keywords": ["power", "generation", "capacity"]},
    "road_length_km": {"units": ["km"], "keywords": ["road", "highway", "length"]},
    "built_up_area_sqm": {"units": ["sqm", "sq m", "square meter"], "keywords": ["built up", "construction", "area"]},
    "dam_height_m": {"units": ["m", "meter"], "keywords": ["dam", "height"]},
    "forest_land_area_ha": {"units": ["ha", "hectare"], "keywords": ["forest", "land"]},
    "sand_extraction_m3_per_year": {"units": ["m3 per year", "cubic meters per year", "cum/year", "m3/year"],
                                    "keywords": ["sand", "extraction", "mining"]},
    "mining_lease_area_ha": {"units": ["ha", "hectare"], "keywords": ["lease area", "mining area", "iron ore", "coal", "sand"]},
    "coal_production_mtpA": {"units": ["mtpa"], "keywords": ["coal", "production"]},
    "minor_mineral_area_ha": {"units": ["ha"], "keywords": ["stone quarry", "mineral area"]}
}

MINING_FIELDS = ["mining_lease_area_ha", "coal_production_mtpA", "sand_extraction_m3_per_year", "minor_mineral_area_ha"]


# ------------------ Numeric Parser ------------------
def parse_numeric_fields(text: str, patterns: dict) -> dict:
    """
    Generic numeric parser for all numeric fields.
    """
    results = {}
    text_lower = text.lower()
    for field, rule in patterns.items():
        units = rule.get("units", [])
        keywords = rule.get("keywords", [])
        for unit in units:
            if not unit:
                continue
            pattern = rf"([\d,]+(?:\.\d+)?)\s*{unit}\b"
            match = re.search(pattern, text_lower)
            if match and any(k in text_lower for k in keywords):
                results[field] = float(match.group(1).replace(',', ''))
                break
    return results


# ------------------ Chat Endpoint ------------------
@app.post("/chat")
def chat(user_message: str):
    # 1️⃣ Extract fields using LLM
    extracted = extractor.extract(user_message)
    conversation.merge(extracted)

    # 2️⃣ CAF fallback
    caf_fallback = extract_caf_fields(user_message)
    conversation.raw_input.setdefault("caf", {})
    conversation.raw_input["caf"].update(caf_fallback)

    # 3️⃣ Extract numeric fields
    numeric_values = parse_numeric_fields(user_message, NUMERIC_PATTERNS)
    conversation.raw_input.setdefault("form1_part_a", {})
    conversation.raw_input.setdefault("derived_parameters", {})

    # 4️⃣ Map numeric fields generically to derived_parameters

    for field, value in numeric_values.items():
        if field not in conversation.raw_input["form1_part_a"]:
            if field in MINING_FIELDS:
                target_field = "max_mining_area_ha" if field == "mining_lease_area_ha" else field
                conversation.raw_input["derived_parameters"][target_field] = float(value)
                conversation.raw_input[target_field] = float(value)
            else:
                conversation.raw_input["form1_part_a"][field] = float(value)

    print("Raw input after numeric mapping:", json.dumps(conversation.raw_input, indent=2))  # Add this
    # 5️⃣ Call DSS API for error handling
    try:
        response = requests.post(DSS_API_URL, json=conversation.raw_input, timeout=10)
        response.raise_for_status()
        response = response.json()
    except requests.RequestException as e:
        return {"error": f"DSS API failed: {str(e)}"}
    
    # 6️⃣ Handle missing mandatory fields (iterative)
    if response.get("status") == "UNDETERMINED":
        missing = response.get("missing_fields", [])
        conversation.pending_fields = missing  # Fixed: Store for iteration
        return {
            "message": "I need more info:\n- " + "\n- ".join([f"Please provide {f}." for f in missing]),
            "pending_fields": missing,
            "current_data": conversation.raw_input
        }

    # 7️⃣ Return final
    return {"message": f"Category {response['category']}", "details": response}


@app.post("/reset")
def reset():
    conversation.reset()
    return {"message": "Conversation reset"}
