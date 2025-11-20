import json
import os
from config import DB_FILE

def load_data():
    """Loads the asset database from the JSON file."""
    if not os.path.exists(DB_FILE):
        return {
            "subdomains": [],
            "live_hosts": [],
            "js_files": {},
            "scanned_ports": {}
        }
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {
            "subdomains": [],
            "live_hosts": [],
            "js_files": {},
            "scanned_ports": {}
        }

def save_data(data):
    """Saves the asset database to the JSON file."""
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def update_subdomains(new_subdomains):
    """Updates the list of subdomains and returns the new ones."""
    data = load_data()
    existing_subdomains = set(data.get("subdomains", []))
    new_set = set(new_subdomains)
    
    added_subdomains = list(new_set - existing_subdomains)
    
    if added_subdomains:
        data["subdomains"] = list(existing_subdomains.union(new_set))
        save_data(data)
        
    return added_subdomains

def get_subdomains():
    """Returns the list of known subdomains."""
    data = load_data()
    return data.get("subdomains", [])
