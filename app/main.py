from fastapi import FastAPI, Query, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse
from app.pipeline import ClassificationPipeline
from pathlib import Path
import shutil
import subprocess
import json
from datetime import datetime

app = FastAPI(
    title="Parivesh DSS Classification API",
    version="1.0"
)

pipeline = ClassificationPipeline(config_dir="app/config")


# Redirect root URL to Swagger UI
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.post("/classify")
def classify_project(payload: dict, debug: bool = Query(False)):
    return pipeline.run(payload, debug)


# ============================================================================
# ADMIN ENDPOINTS - Rules Management
# ============================================================================

@app.post("/admin/refresh-rules")
async def refresh_rules_from_excel(
    excel_file: UploadFile = File(...),
    force: bool = False
):
    """
    Manual trigger to REPLACE all DSS rules from uploaded Excel file.
    WARNING: This replaces ALL existing rules. Use /admin/merge-rules to add new rules without deleting old ones.
    
    **Parameters:**
    - `excel_file`: Excel file containing updated rules
    - `force`: If True, overwrites existing rules without backup
    
    **Returns:**
    - Status of the conversion
    - Summary of updated rules
    
    **Example Usage:**
    ```bash
    curl -X POST "http://localhost:8000/admin/refresh-rules" \
      -F "excel_file=@path/to/rules.xlsx"
    ```
    """
    
    # Define paths
    upload_dir = Path("app/config/excel_uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_path = upload_dir / f"dss_rules_{timestamp}.xlsx"
    json_output = Path("app/config/dss_rules.json")
    backup_path = Path(f"app/config/dss_rules_backup_{timestamp}.json")
    
    try:
        # Validate file type
        if not excel_file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Please upload an Excel file (.xlsx or .xls)"
            )
        
        # Save uploaded Excel file
        with open(excel_path, "wb") as buffer:
            content = await excel_file.read()
            buffer.write(content)
        
        print(f"Excel file uploaded: {excel_path}")
        
        # Backup existing rules if not forcing
        if json_output.exists() and not force:
            shutil.copy(json_output, backup_path)
            print(f"Backup created: {backup_path}")
        
        # Run converter
        converter_script = Path("excel_to_json_converter.py")
        
        if not converter_script.exists():
            raise HTTPException(
                status_code=500,
                detail="Converter script not found. Please ensure excel_to_json_converter.py is in the project root."
            )
        
        result = subprocess.run(
            [
                "python",
                str(converter_script),
                "--excel", str(excel_path),
                "--output", str(json_output)
            ],
            capture_output=True,
            text=True,
            cwd="."
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Conversion failed: {result.stderr}"
            )
        
        # Load and verify new rules
        with open(json_output) as f:
            new_rules = json.load(f)
        
        # Reload pipeline configuration
        global pipeline
        pipeline = ClassificationPipeline(config_dir="app/config")
        
        # Generate summary
        summary = {
            "status": "success",
            "message": "Rules successfully updated and pipeline reloaded",
            "timestamp": datetime.now().isoformat(),
            "excel_file": excel_file.filename,
            "saved_as": excel_path.name,
            "sectors": list(new_rules.keys()),
            "total_activities": sum(len(activities) for activities in new_rules.values()),
            "activities_per_sector": {
                sector: len(activities)
                for sector, activities in new_rules.items()
            },
            "backup_created": backup_path.exists() and not force,
            "backup_file": backup_path.name if backup_path.exists() else None,
            "converter_output": result.stdout
        }
        
        return summary
        
    except Exception as e:
        # Restore from backup if something went wrong
        if backup_path.exists() and json_output.exists():
            shutil.copy(backup_path, json_output)
            print(f"Error occurred, restored from backup")
        
        raise HTTPException(
            status_code=500,
            detail=f"Error during rule refresh: {str(e)}"
        )


@app.post("/admin/merge-rules")
async def merge_rules_from_excel(
    excel_file: UploadFile = File(...),
    force: bool = False
):
    """
    Merge new DSS rules from uploaded Excel file with existing rules.
    Existing rules are preserved, new activities are added, duplicate activities are updated.
    
    **Parameters:**
    - `excel_file`: Excel file containing new/updated rules
    - `force`: If True, skips backup creation
    
    **Returns:**
    - Status of the merge operation
    - Summary of added/updated rules
    
    **Example Usage:**
    ```bash
    curl -X POST "http://localhost:8000/admin/merge-rules" \
      -F "excel_file=@path/to/new_rules.xlsx"
    ```
    """
    
    # Define paths
    upload_dir = Path("app/config/excel_uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_path = upload_dir / f"dss_rules_merge_{timestamp}.xlsx"
    json_output = Path("app/config/dss_rules.json")
    backup_path = Path(f"app/config/dss_rules_backup_{timestamp}.json")
    
    try:
        # Validate file type
        if not excel_file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Please upload an Excel file (.xlsx or .xls)"
            )
        
        # Save uploaded Excel file
        with open(excel_path, "wb") as buffer:
            content = await excel_file.read()
            buffer.write(content)
        
        print(f"Excel file uploaded for merge: {excel_path}")
        
        # Backup existing rules if not forcing
        if json_output.exists() and not force:
            shutil.copy(json_output, backup_path)
            print(f"Backup created: {backup_path}")
        
        # Run converter with --merge flag
        converter_script = Path("excel_to_json_converter.py")
        
        if not converter_script.exists():
            raise HTTPException(
                status_code=500,
                detail="Converter script not found. Please ensure excel_to_json_converter.py is in the project root."
            )
        
        result = subprocess.run(
            [
                "python",
                str(converter_script),
                "--excel", str(excel_path),
                "--output", str(json_output),
                "--merge"  # This is the key addition!
            ],
            capture_output=True,
            text=True,
            cwd="."
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Merge failed: {result.stderr}"
            )
        
        # Load and verify merged rules
        with open(json_output) as f:
            merged_rules = json.load(f)
        
        # Reload pipeline configuration
        global pipeline
        pipeline = ClassificationPipeline(config_dir="app/config")
        
        # Generate summary
        summary = {
            "status": "success",
            "message": "Rules successfully merged and pipeline reloaded",
            "operation": "MERGE",
            "timestamp": datetime.now().isoformat(),
            "excel_file": excel_file.filename,
            "saved_as": excel_path.name,
            "sectors": list(merged_rules.keys()),
            "total_activities": sum(len(activities) for activities in merged_rules.values()),
            "activities_per_sector": {
                sector: len(activities)
                for sector, activities in merged_rules.items()
            },
            "backup_created": backup_path.exists() and not force,
            "backup_file": backup_path.name if backup_path.exists() else None,
            "converter_output": result.stdout
        }
        
        return summary
        
    except Exception as e:
        # Restore from backup if something went wrong
        if backup_path.exists() and json_output.exists():
            shutil.copy(backup_path, json_output)
            print(f"Error occurred, restored from backup")
        
        raise HTTPException(
            status_code=500,
            detail=f"Error during rule merge: {str(e)}"
        )



@app.get("/admin/rules-status")
def get_rules_status():
    """
    Get current status and statistics of DSS rules.
    
    **Returns:**
    - Current rules summary
    - Last modified timestamp
    - Available backups
    - Activity breakdown by sector
    
    **Example Usage:**
    ```bash
    curl http://localhost:8000/admin/rules-status
    ```
    """
    json_path = Path("app/config/dss_rules.json")
    backup_dir = Path("app/config")
    
    if not json_path.exists():
        return {
            "status": "no_rules_found",
            "message": "DSS rules JSON file not found. Please upload rules using /admin/refresh-rules"
        }
    
    try:
        # Load current rules
        with open(json_path) as f:
            rules = json.load(f)
        
        # Get file stats
        stats = json_path.stat()
        
        # Find all backups
        backups = list(backup_dir.glob("dss_rules_backup_*.json"))
        backup_info = []
        for backup in sorted(backups, reverse=True)[:5]:  # Last 5 backups
            backup_stats = backup.stat()
            backup_info.append({
                "filename": backup.name,
                "timestamp": datetime.fromtimestamp(backup_stats.st_mtime).isoformat(),
                "size_kb": round(backup_stats.st_size / 1024, 2)
            })
        
        return {
            "status": "active",
            "last_modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
            "file_size_kb": round(stats.st_size / 1024, 2),
            "sectors": list(rules.keys()),
            "total_activities": sum(len(activities) for activities in rules.values()),
            "activities_per_sector": {
                sector: len(activities)
                for sector, activities in rules.items()
            },
            "total_backups": len(backups),
            "recent_backups": backup_info
        }
    except json.JSONDecodeError:
        return {
            "status": "error",
            "message": "Rules file exists but contains invalid JSON"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading rules status: {str(e)}"
        )


@app.post("/admin/rollback-rules")
def rollback_to_backup(backup_filename: str = None):
    """
    Rollback to a specific backup version of rules.
    
    **Parameters:**
    - `backup_filename`: Optional specific backup file to restore.
                        If not provided, uses the most recent backup.
    
    **Returns:**
    - Status of rollback operation
    
    **Example Usage:**
    ```bash
    # Rollback to most recent backup
    curl -X POST http://localhost:8000/admin/rollback-rules
    
    # Rollback to specific backup
    curl -X POST "http://localhost:8000/admin/rollback-rules?backup_filename=dss_rules_backup_20250204_103000.json"
    ```
    """
    json_path = Path("app/config/dss_rules.json")
    backup_dir = Path("app/config")
    
    try:
        # Find backup file
        if backup_filename:
            backup_path = backup_dir / backup_filename
            if not backup_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Backup file not found: {backup_filename}"
                )
        else:
            # Find most recent backup
            backups = list(backup_dir.glob("dss_rules_backup_*.json"))
            if not backups:
                raise HTTPException(
                    status_code=404,
                    detail="No backup files found. Cannot rollback."
                )
            backup_path = max(backups, key=lambda p: p.stat().st_mtime)
        
        # Create a pre-rollback backup of current state
        pre_rollback_backup = None
        if json_path.exists():
            pre_rollback_backup = backup_dir / f"dss_rules_pre_rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            shutil.copy(json_path, pre_rollback_backup)
            print(f"Pre-rollback backup created: {pre_rollback_backup}")
        
        # Restore from backup
        shutil.copy(backup_path, json_path)
        
        # Reload pipeline
        global pipeline
        pipeline = ClassificationPipeline(config_dir="app/config")
        
        return {
            "status": "success",
            "message": "Rules successfully rolled back and pipeline reloaded",
            "timestamp": datetime.now().isoformat(),
            "restored_from": backup_path.name,
            "pre_rollback_backup": pre_rollback_backup.name if pre_rollback_backup else None
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Rollback failed: {str(e)}"
        )


@app.get("/admin/list-backups")
def list_all_backups():
    """
    List all available backup files.
    
    **Returns:**
    - List of all backup files with metadata
    
    **Example Usage:**
    ```bash
    curl http://localhost:8000/admin/list-backups
    ```
    """
    backup_dir = Path("app/config")
    backups = list(backup_dir.glob("dss_rules_backup_*.json"))
    
    if not backups:
        return {
            "status": "no_backups",
            "message": "No backup files found",
            "backups": []
        }
    
    backup_list = []
    for backup in sorted(backups, reverse=True):
        stats = backup.stat()
        backup_list.append({
            "filename": backup.name,
            "created": datetime.fromtimestamp(stats.st_mtime).isoformat(),
            "size_kb": round(stats.st_size / 1024, 2),
            "age_hours": round((datetime.now().timestamp() - stats.st_mtime) / 3600, 1)
        })
    
    return {
        "status": "success",
        "total_backups": len(backups),
        "backups": backup_list
    }


@app.delete("/admin/cleanup-old-backups")
def cleanup_old_backups(keep_last: int = 10):
    """
    Clean up old backup files, keeping only the most recent ones.
    
    **Parameters:**
    - `keep_last`: Number of most recent backups to keep (default: 10)
    
    **Returns:**
    - Number of files deleted
    
    **Example Usage:**
    ```bash
    curl -X DELETE "http://localhost:8000/admin/cleanup-old-backups?keep_last=5"
    ```
    """
    backup_dir = Path("app/config")
    backups = sorted(
        backup_dir.glob("dss_rules_backup_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    if len(backups) <= keep_last:
        return {
            "status": "no_action",
            "message": f"Only {len(backups)} backups exist, keeping all",
            "deleted": 0
        }
    
    to_delete = backups[keep_last:]
    deleted_files = []
    
    for backup in to_delete:
        try:
            backup.unlink()
            deleted_files.append(backup.name)
        except Exception as e:
            print(f"Failed to delete {backup}: {e}")
    
    return {
        "status": "success",
        "message": f"Cleaned up {len(deleted_files)} old backups",
        "kept": keep_last,
        "deleted": len(deleted_files),
        "deleted_files": deleted_files
    }


# Startup event - show URLs
@app.on_event("startup")
def show_docs_url():
    print("Parivesh DSS API is running")
    print("Swagger UI available at: http://127.0.0.1:8000/docs")
    print("\nAdmin Endpoints:")
    print("   - POST /admin/refresh-rules        - Upload new rules Excel (REPLACES all)")
    print("   - POST /admin/merge-rules          - Upload new rules Excel (MERGES with existing)")
    print("   - GET  /admin/rules-status         - Check current rules")
    print("   - POST /admin/rollback-rules       - Rollback to backup")
    print("   - GET  /admin/list-backups         - List all backups")
    print("   - DELETE /admin/cleanup-old-backups - Clean old backups")
