# API Documentation

## Base URL
```
http://localhost:8000
```

## Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Endpoints

### **Classification**

#### `POST /classify`
Classify a project based on provided parameters.

**Request Body:**
```json
{
  "sector": "industry",
  "activity": "cement",
  "effective_capacity": 2.5,
  "state": "Maharashtra",
  "district": "Pune"
}
```

**Response (Success - Classified):**
```json
{
  "status": "CLASSIFIED",
  "category": "A",
  "reason": "Cement plant >= 2.0 MTPA",
  "sector": "industry",
  "activity": "cement",
  "matched_activity": "cement"
}
```

**Response (Undetermined - Missing Fields):**
```json
{
  "status": "UNDETERMINED",
  "reason": "Missing mandatory fields",
  "missing_fields": ["sector", "activity", "state", "district"]
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "sector": "industry",
    "activity": "paper mill",
    "effective_capacity": 250
  }'
```

---

### **Admin Endpoints**

#### `POST /admin/refresh-rules`
Replace ALL existing rules from uploaded Excel file.

> **⚠️ WARNING**: This replaces all existing rules. Use `/admin/merge-rules` to add new rules without deleting existing ones.

**Parameters:**
- `excel_file` (file, required): Excel file containing rules
- `force` (boolean, optional): Skip backup creation if true

**Request (multipart/form-data):**
```bash
curl -X POST "http://localhost:8000/admin/refresh-rules" \
  -F "excel_file=@rules.xlsx" \
  -F "force=false"
```

**Response:**
```json
{
  "status": "success",
  "message": "Rules successfully updated and pipeline reloaded",
  "timestamp": "2026-02-05T22:00:00",
  "excel_file": "rules.xlsx",
  "sectors": ["mining", "industry", "infrastructure"],
  "total_activities": 15,
  "activities_per_sector": {
    "mining": 5,
    "industry": 5,
    "infrastructure": 5
  },
  "backup_created": true,
  "backup_file": "dss_rules_backup_20260205_220000.json"
}
```

---

#### `POST /admin/merge-rules`
Merge new rules from Excel with existing rules (preserves existing rules).

**Parameters:**
- `excel_file` (file, required): Excel file containing new/updated rules
- `force` (boolean, optional): Skip backup creation if true

**Request:**
```bash
curl -X POST "http://localhost:8000/admin/merge-rules" \
  -F "excel_file=@new_rules.xlsx"
```

**Response:**
```json
{
  "status": "success",
  "message": "Rules successfully merged and pipeline reloaded",
  "operation": "MERGE",
  "timestamp": "2026-02-05T22:05:00",
  "sectors": ["mining", "industry", "infrastructure"],
  "total_activities": 18,
  "backup_created": true
}
```

---

#### `GET /admin/rules-status`
Get current status and statistics of classification rules.

**Request:**
```bash
curl http://localhost:8000/admin/rules-status
```

**Response:**
```json
{
  "status": "active",
  "last_modified": "2026-02-05T22:00:00",
  "file_size_kb": 9.48,
  "sectors": ["mining", "industry", "infrastructure"],
  "total_activities": 15,
  "activities_per_sector": {
    "mining": 5,
    "industry": 5,
    "infrastructure": 5
  },
  "total_backups": 3,
  "recent_backups": [
    {
      "filename": "dss_rules_backup_20260205_220000.json",
      "timestamp": "2026-02-05T22:00:00",
      "size_kb": 9.32
    }
  ]
}
```

---

#### `POST /admin/rollback-rules`
Rollback to a previous backup version of rules.

**Parameters:**
- `backup_filename` (string, optional): Specific backup file to restore. If not provided, uses the most recent backup.

**Request:**
```bash
# Rollback to most recent backup
curl -X POST "http://localhost:8000/admin/rollback-rules"

# Rollback to specific backup
curl -X POST "http://localhost:8000/admin/rollback-rules?backup_filename=dss_rules_backup_20260205_220000.json"
```

**Response:**
```json
{
  "status": "success",
  "message": "Rules successfully rolled back and pipeline reloaded",
  "timestamp": "2026-02-05T22:10:00",
  "restored_from": "dss_rules_backup_20260205_220000.json",
  "pre_rollback_backup": "dss_rules_pre_rollback_20260205_221000.json"
}
```

---

#### `GET /admin/list-backups`
List all available backup files.

**Request:**
```bash
curl http://localhost:8000/admin/list-backups
```

**Response:**
```json
{
  "status": "success",
  "total_backups": 5,
  "backups": [
    {
      "filename": "dss_rules_backup_20260205_220000.json",
      "created": "2026-02-05T22:00:00",
      "size_kb": 9.32,
      "age_hours": 0.2
    },
    {
      "filename": "dss_rules_backup_20260204_150000.json",
      "created": "2026-02-04T15:00:00",
      "size_kb": 8.45,
      "age_hours": 31.0
    }
  ]
}
```

---

#### `DELETE /admin/cleanup-old-backups`
Clean up old backup files, keeping only the most recent ones.

**Parameters:**
- `keep_last` (integer, optional): Number of most recent backups to keep (default: 10)

**Request:**
```bash
curl -X DELETE "http://localhost:8000/admin/cleanup-old-backups?keep_last=5"
```

**Response:**
```json
{
  "status": "success",
  "message": "Cleaned up 3 old backups",
  "kept": 5,
  "deleted": 3,
  "deleted_files": [
    "dss_rules_backup_20260201_100000.json",
    "dss_rules_backup_20260131_140000.json",
    "dss_rules_backup_20260130_090000.json"
  ]
}
```

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid file type. Please upload an Excel file (.xlsx or .xls)"
}
```

### 404 Not Found
```json
{
  "detail": "Backup file not found: dss_rules_backup_20260205_220000.json"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Error during rule refresh: <error message>"
}
```

---

## Field Specifications

### Common Project Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `sector` | string | Project sector | "industry", "mining", "infrastructure" |
| `activity` | string | Specific activity | "cement", "coal mining", "highway project" |
| `state` | string | State location | "Maharashtra" |
| `district` | string | District location | "Pune" |
| `effective_capacity` | number | Production capacity (industry) | 2.5 (MTPA) |
| `power_generation_mw` | number | Power generation capacity | 500 (MW) |
| `road_length_km` | number | Road/highway length | 150 (km) |
| `built_up_area_sqm` | number | Construction area | 200000 (sqm) |
| `max_mining_area_ha` | number | Mining lease area | 100 (hectares) |

---

## Status Codes

- **200 OK**: Request successful
- **400 Bad Request**: Invalid input parameters
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error
