import re
from fastapi import FastAPI
import requests

from llm_agent.extractor import FieldExtractor
from llm_agent.conversation import ConversationState

ACTIVITY_RESOLVER = {
    "cement": "cement",
    "cement plant": "cement",
    "cement factory": "cement",

    "steel": "steel plant",
    "steel plant": "steel plant",

    "thermal": "thermal power plant",
    "thermal power plant": "thermal power plant",

    "sugar": "sugar industry",
    "sugar mill": "sugar industry",
    "sugar factory": "sugar industry",

    "highway": "highway project",
    "road": "highway project",

    "construction": "construction project",
    "building": "construction project",

    "hydro": "hydroelectric project",
    "hydroelectric": "hydroelectric project",

    "coal mining": "coal mining",
    "iron ore": "iron ore",
    "sand mining": "sand mining"
}

HUMAN_FIELD_MAP = {
    "effective_capacity": "What is the proposed capacity of the project (in MTPA)?",
    "activity": "What is the main activity of the project (e.g., cement plant, steel plant, highway, etc.)?",
    "project_activity": "What is the main activity of the project (e.g., cement plant, steel plant, highway, etc.)?",
    "state": "Which state is the project located in?",
    "district": "Which district is the project located in?",
    "type_of_proposal": "Is this a new project or an expansion?"
}

NUMERIC_PATTERNS = {
    "proposed_capacity": {
        "units": ["mtpa"],
        "keywords": ["capacity", "production", "plant capacity"]
    },
    "power_generation_mw": {
        "units": ["mw"],
        "keywords": ["power", "generation", "capacity"]
    },
    "road_length_km": {
        "units": ["km"],
        "keywords": ["road", "highway", "length"]
    },
    "built_up_area_sqm": {
        "units": ["sqm", "sq m", "square meter"],
        "keywords": ["built up", "construction", "area"]
    },
    "dam_height_m": {
        "units": ["m", "meter"],
        "keywords": ["dam", "height"]
    },
    "forest_land_area_ha": {
        "units": ["ha", "hectare"],
        "keywords": ["forest", "land"]
    }
}



DSS_API_URL = "http://127.0.0.1:8000/classify"

app = FastAPI(title="Parivesh LLM Agent")

extractor = FieldExtractor()
conversation = ConversationState()


@app.post("/chat")
def chat(user_message: str):
    # 1️⃣ Extract fields from user text
    extracted = extractor.extract(user_message)

    # 2️⃣ Merge into conversation state
    conversation.merge(extracted)
    # 🔑 Context-aware numeric extraction
    text = user_message.lower()

    for field, rule in NUMERIC_PATTERNS.items():
        for unit in rule["units"]:
            pattern = rf"(\d+(\.\d+)?)\s*{unit}"
            match = re.search(pattern, text)

            if match and any(k in text for k in rule["keywords"]):
                value = float(match.group(1))
                conversation.raw_input.setdefault("form1_part_a", {})
                conversation.raw_input["form1_part_a"].setdefault(field, value)



    # 3️⃣ Call DSS API
    response = requests.post(
        DSS_API_URL,
        json=conversation.raw_input
    ).json()

    # 4️⃣ Handle missing mandatory fields
    if response.get("status") == "UNDETERMINED":
        missing = response.get("missing_fields", [])

        questions = [
            HUMAN_FIELD_MAP.get(
                field,
                f"Please provide information for {field}."
            )
            for field in missing
        ]

        return {
            "message": "I need some more information to proceed:\n- " + "\n- ".join(questions),
            "pending_fields": missing,
            "current_data": conversation.raw_input
        }


    # 5️⃣ Final classified response
    return {
        "message": f"Project classified as Category {response['category']}",
        "details": response
    }


@app.post("/reset")
def reset():
    conversation.reset()
    return {"message": "Conversation reset"}
