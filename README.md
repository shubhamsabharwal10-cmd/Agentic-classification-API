# Rule-Based Classification API

An intelligent classification API that combines LLM-powered field extraction with rule-based categorization to help users quickly determine regulatory requirements and permissions for their projects. Eliminates the time-consuming process of navigating complex paperwork and authority hierarchies.

## 🎯 What Problem Does This Solve?

When working on projects that require regulatory approval, people often spend significant time figuring out:
- What permissions they need
- Which

 authority to approach  
- What category their project falls under

This API **automates that entire process** by:
1. Extracting project details from natural language input using LLM
2. Applying configurable rule-based classification
3. Providing instant categorization and next steps

---

## ✨ Key Features

- 🤖 **LLM-Powered Extraction** - Automatically extract project details from user input
- 📊 **Rule-Based Classification** - Apply complex multi-tier classification rules
- 📝 **Excel Rule Management** - Easily update rules via Excel uploads
- 🔄 **Dynamic Rule Updates** - Add or merge rules without downtime
- 🔐 **Backup & Rollback** - Automatic backups with rollback capability
- ⚡ **FastAPI** - High-performance REST API with auto-generated docs
- 🎨 **Interactive Swagger UI** - Test endpoints directly in the browser

---

## 🛠️ Tech Stack

- **Framework**: FastAPI
- **LLM Integration**: AWS Bedrock (Claude 3.5)
- **Validation**: Pydantic
- **Excel Processing**: OpenPyXL, Pandas
- **Server**: Uvicorn

---

## 📦 Installation & Setup

### Prerequisites
- Python 3.8+
- AWS Account with Bedrock access (for LLM features)

### Step 1: Clone the Repository
```bash
git clone https://github.com/shubhamsabharwal10-cmd/Agentic-classification-API.git
cd Agentic-classification-API
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your AWS credentials
# (Required only if using LLM extraction features)
```

### Step 5: Run the API
```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at: **http://localhost:8000**  
Swagger UI documentation: **http://localhost:8000/docs**

---

## 🚀 Quick Start

### Example 1: Classify a Project
```bash
curl -X POST "http://localhost:8000/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "sector": "industry",
    "activity": "cement",
    "effective_capacity": 2.5
  }'
```

**Response:**
```json
{
  "status": "CLASSIFIED",
  "category": "A",
  "reason": "Cement plant >= 2.0 MTPA",
  "sector": "industry",
  "activity": "cement"
}
```

### Example 2: Upload New Rules
```bash
curl -X POST "http://localhost:8000/admin/refresh-rules" \
  -F "excel_file=@path/to/rules.xlsx"
```

---

## 📁 Project Structure

```
Agentic-classification-API/
├── app/
│   ├── main.py                  # FastAPI application
│   ├── pipeline.py              # Classification pipeline
│   ├── rule_engine.py           # Rule evaluation logic
│   ├── field_mapper.py          # Field mapping utilities
│   ├── mandatory_validator.py   # Field validation
│   ├── activity_similarity.py   # Activity matching
│   ├── capacity_normalizer.py   # Unit conversion
│   ├── override_evaluator.py    # Override rules logic
│   └── config/
│       ├── dss_rules.json       # Main classification rules
│       ├── field_mapping.json   # Field mappings
│       ├── mandatory_fields.json # Required fields
│       └── override_rules.json  # Override rules
│
├── llm_agent/
│   ├── main.py                  # LLM agent
│   ├── extractor.py             # Field extraction logic
│   ├── bedrock_client.py        # AWS Bedrock client
│   ├── schemas.py               # Pydantic models
│   └── conversation.py          # Conversation state
│
├── excel_to_json_converter.py  # Excel → JSON converter
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
└── README.md                    # This file
```

---

## 🔌 API Endpoints

### Classification
- **POST `/classify`** - Classify a project based on input parameters

### Admin - Rule Management
- **POST `/admin/refresh-rules`** - Replace all rules from Excel (creates backup)
- **POST `/admin/merge-rules`** - Merge new rules with existing ones
- **GET `/admin/rules-status`** - Get current rules statistics
- **POST `/admin/rollback-rules`** - Rollback to a previous backup
- **GET `/admin/list-backups`** - List all available backups
- **DELETE `/admin/cleanup-old-backups`** - Clean up old backup files

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for detailed endpoint documentation.

---

## 📚 Documentation

- **[API Documentation](API_DOCUMENTATION.md)** - Detailed API endpoint reference
- **[Architecture Overview](ARCHITECTURE.md)** - System architecture and design
- **[Examples](examples/)** - Sample requests and usage examples

---

## 🔧 Configuration

### Updating Classification Rules

Rules can be updated via Excel files using the admin endpoints:

1. **Prepare Excel File**: Use the format in `examples/sample_rules.xlsx`
2. **Upload**: Use `/admin/refresh-rules` or `/admin/merge-rules` endpoint
3. **Verify**: Check `/admin/rules-status` to confirm updates

The system automatically creates backups before any rule updates.

---

## 🧪 Testing

Access the **Swagger UI** at `http://localhost:8000/docs` to:
- View all available endpoints
- Test API calls interactively  
- See request/response schemas
- Download OpenAPI specification

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details

---

## 👤 Author

**Shubham Sabharwal**  
GitHub: [@shubhamsabharwal10-cmd](https://github.com/shubhamsabharwal10-cmd)

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

---

## ⭐ Show Your Support

Give a ⭐️ if this project helped you!
