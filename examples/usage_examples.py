"""
Example usage of the Rule-Based Classification API

This script demonstrates how to interact with the API programmatically.
"""

import requests
import json

# API Base URL
BASE_URL = "http://localhost:8000"

def classify_project(project_data):
    """Classify a project using the API."""
    url = f"{BASE_URL}/classify"
    response = requests.post(url, json=project_data)
    return response.json()

def get_rules_status():
    """Get current rules status."""
    url = f"{BASE_URL}/admin/rules-status"
    response = requests.get(url)
    return response.json()

def upload_rules(excel_file_path, merge=False):
    """Upload new rules from Excel file."""
    endpoint = "merge-rules" if merge else "refresh-rules"
    url = f"{BASE_URL}/admin/{endpoint}"
    
    with open(excel_file_path, 'rb') as f:
        files = {'excel_file': f}
        response = requests.post(url, files=files)
    
    return response.json()

# Example 1: Classify a cement plant
print("=" * 60)
print("Example 1: Classify a Cement Plant (Category A)")
print("=" * 60)

cement_project = {
    "sector": "industry",
    "activity": "cement",
    "effective_capacity": 2.5,
    "state": "Maharashtra",
    "district": "Pune"
}

result = classify_project(cement_project)
print(json.dumps(result, indent=2))

# Example 2: Classify a paper mill (Category B1)
print("\n" + "=" * 60)
print("Example 2: Classify a Paper Mill (Category B1)")
print("=" * 60)

paper_mill_project = {
    "sector": "industry",
    "activity": "paper mill",
    "effective_capacity": 150,
    "state": "Karnataka",
    "district": "Bangalore"
}

result = classify_project(paper_mill_project)
print(json.dumps(result, indent=2))

# Example 3: Missing mandatory fields
print("\n" + "=" * 60)
print("Example 3: Missing Mandatory Fields")
print("=" * 60)

incomplete_project = {
    "sector": "industry",
    "activity": "steel plant"
    # Missing: effective_capacity, state, district
}

result = classify_project(incomplete_project)
print(json.dumps(result, indent=2))

# Example 4: Get Rules Status
print("\n" + "=" * 60)
print("Example 4: Get Current Rules Status")
print("=" * 60)

status = get_rules_status()
print(json.dumps(status, indent=2))

# Example 5: Upload Rules (uncomment to test)
# print("\n" + "=" * 60)
# print("Example 5: Upload New Rules from Excel")
# print("=" * 60)
# 
# result = upload_rules("path/to/rules.xlsx", merge=True)
# print(json.dumps(result, indent=2))
