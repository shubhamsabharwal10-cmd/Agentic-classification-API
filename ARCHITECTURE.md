# System Architecture

## Overview

The Rule-Based Classification API is a **multi-layered architecture** combining LLM-powered extraction with rule-based classification. The system is designed for **flexibility, extensibility, and ease of maintenance**.

```
┌─────────────────────────────────────────────────────────────────┐
│                          CLIENT REQUEST                          │
│                     (HTTP POST /classify)                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────────────┐
│                       FASTAPI APPLICATION                          │
│                        (app/main.py)                               │
│  • Request validation                                              │
│  • Route handling                                                  │
│  • Response formatting                                             │
└──────────────────────────┬────────────────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────────────┐
│                    CLASSIFICATION PIPELINE                         │
│                      (app/pipeline.py)                             │
│                                                                    │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐        │
│  │   Field     │ -> │  Mandatory   │ -> │     Rule     │        │
│  │   Mapper    │    │  Validator   │    │    Engine    │        │
│  └─────────────┘    └──────────────┘    └──────────────┘        │
│                                                                    │
└──────────────────────────┬────────────────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────────────┐
│                         RULE ENGINE                                │
│                      (app/rule_engine.py)                          │
│  • Evaluate classification rules                                   │
│  • Match activity similarity                                       │
│  • Normalize capacity units                                        │
│  • Apply override rules                                            │
└───────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. **FastAPI Application Layer** (`app/main.py`)

**Responsibilities:**
- HTTP request/response handling
- Route definitions for classification and admin endpoints
- Swagger UI documentation
- File upload handling (Excel rules)
- Error handling and validation

**Key Endpoints:**
- `/classify` - Main classification endpoint
- `/admin/*` - Rule management endpoints

---

### 2. **Classification Pipeline** (`app/pipeline.py`)

**Responsibilities:**
- Orchestrates the classification workflow
- Coordinates field mapping, validation, and rule evaluation
- Returns structured classification results

**Workflow:**
```
Input → Field Mapping → Validation → Rule Evaluation → Output
```

---

### 3. **Rule Engine** (`app/rule_engine.py`)

**Responsibilities:**
- Load classification rules from JSON
- Evaluate rules against project parameters
- Apply conditional logic (>=, >, ==, etc.)
- Handle complex conditions (AND, OR logic)

**Rule Structure:**
```json
{
  "sector": {
    "activity": [
      {
        "category": "A",
        "reason": "Capacity >= 2.0 MTPA",
        "condition": {
          "field": "effective_capacity",
          "op": ">=",
          "value": 2.0
        }
      }
    ]
  }
}
```

---

### 4. **Field Mapper** (`app/field_mapper.py`)

**Responsibilities:**
- Map user-provided fields to internal field names
- Handle field aliases and synonyms
- Normalize field names for consistency

---

### 5. **Mandatory Validator** (`app/mandatory_validator.py`)

**Responsibilities:**
- Validate presence of required fields
- Return missing field errors
- Ensure data completeness before classification

**Configuration:** `app/config/mandatory_fields.json`

---

### 6. **Activity Similarity** (`app/activity_similarity.py`)

**Responsibilities:**
- Fuzzy match user input to known activities
- Handle spelling variations
- Suggest closest matches

**Example:**
```
Input: "cememnt plant" → Matched: "cement"
Input: "paper mill" → Matched: "paper mill"
```

---

### 7. **Capacity Normalizer** (`app/capacity_normalizer.py`)

**Responsibilities:**
- Convert capacity units to standard formats
- Handle TPD, MTPA, MW, hectares, etc.
- Ensure consistent unit comparisons

---

### 8. **Override Evaluator** (`app/override_evaluator.py`)

**Responsibilities:**
- Apply special override rules
- Handle exceptions to standard classification
- Support complex business logic

**Configuration:** `app/config/override_rules.json`

---

### 9. **LLM Agent** (`llm_agent/`)

**Responsibilities:**
- Extract project details from natural language
- Call AWS Bedrock API (Claude 3.5)
- Parse LLM responses into structured data
- Maintain conversation state

**Components:**
- `main.py` - Agent orchestration
- `extractor.py` - Field extraction logic
- `bedrock_client.py` - AWS Bedrock integration
- `schemas.py` - Pydantic data models
- `conversation.py` - Conversation state management

---

### 10. **Excel to JSON Converter** (`excel_to_json_converter.py`)

**Responsibilities:**
- Convert Excel rules to JSON format
- Support merge and replace operations
- Validate rule structure
- Create automatic backups

**Excel Format:**
| Sector | Activity | Threshold Attribute | Units | cat A | cat B1 | cat B2 |
|--------|----------|---------------------|-------|-------|--------|--------|
| IND1   | cement   | production capacity | MTPA  | >=2.0 | >=1.2  | -      |

---

## Data Flow

### **Classification Request Flow**

1. **Client sends POST request** to `/classify`
2. **FastAPI validates** request body
3. **Pipeline executes**:
   - Field Mapper maps fields
   - Mandatory Validator checks required fields
   - Rule Engine evaluates classification rules
   - Activity Similarity matches activity names
   - Capacity Normalizer converts units
4. **Response returned** to client

### **Rule Update Flow**

1. **Admin uploads Excel** via `/admin/refresh-rules` or `/admin/merge-rules`
2. **Excel to JSON Converter** processes file
3. **Backup created** automatically
4. **New rules saved** to `app/config/dss_rules.json`
5. **Pipeline reloaded** with new rules
6. **Success response** returned

---

## Configuration Files

All configuration stored in `app/config/`:

| File | Purpose |
|------|---------|
| `dss_rules.json` | Main classification rules |
| `field_mapping.json` | Field name mappings |
| `mandatory_fields.json` | Required fields per sector |
| `override_rules.json` | Special case overrides |

---

## Scalability & Performance

- **Stateless design**: Each request is independent
- **Fast rule evaluation**: O(n) rule matching
- **Async file handling**: Non-blocking Excel uploads
- **Automatic backups**: No data loss risk
- **Hot reload**: Rules can be updated without server restart

---

## Security Considerations

- **Environment variables**: AWS credentials stored in `.env`
- **Input validation**: Pydantic models validate all inputs
- **File type validation**: Only .xlsx/.xls accepted
- **Backup isolation**: Backups stored separately from active rules

---

## Future Enhancements

- **Database integration**: Store rules in PostgreSQL/MongoDB
- **Caching layer**: Redis for frequently accessed rules
- **Authentication**: Add JWT-based API authentication
- **Rate limiting**: Prevent abuse
- **Logging**: Structured logging with ELK stack
