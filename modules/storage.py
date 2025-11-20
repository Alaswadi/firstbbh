"""
Storage module - Database operations wrapper.
This module provides backward-compatible interface to the database.
"""
import os
from database import (
    init_db,
    get_all_subdomains,
    add_subdomains,
    get_all_scans,
    create_scan,
    update_scan_status,
    get_scan,
    migrate_from_json
)

# Initialize database on module import
init_db()

def load_data():
    """
    Legacy function for backward compatibility.
    Returns data in the old JSON format.
    """
    return {
        "subdomains": get_all_subdomains(),
        "live_hosts": [],
        "js_files": {},
        "scanned_ports": {}
    }

def save_data(data):
    """
    Legacy function for backward compatibility.
    This is a no-op now as database saves automatically.
    """
    pass

def update_subdomains(new_subdomains, domain="unknown", scan_id=None):
    """
    Updates the list of subdomains and returns the new ones.
    Now uses database instead of JSON.
    """
    if not new_subdomains:
        return []
    
    # Add subdomains to database and get list of newly added ones
    added_subdomains = add_subdomains(new_subdomains, domain, scan_id or 0, "discovery")
    
    return added_subdomains

def get_subdomains():
    """Returns the list of known subdomains."""
    return get_all_subdomains()

