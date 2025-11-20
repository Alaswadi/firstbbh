import sqlite3
import json
import os
from datetime import datetime
from contextlib import contextmanager
from config import DATA_DIR, DB_FILE

# Database path
DB_PATH = os.path.join(DATA_DIR, "bbh_automation.db")

@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """Initialize the database schema."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Scans table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                scan_type TEXT NOT NULL,
                status TEXT NOT NULL,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                tools TEXT,
                error_message TEXT
            )
        """)
        
        # Subdomains table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subdomains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subdomain TEXT NOT NULL UNIQUE,
                domain TEXT NOT NULL,
                source TEXT,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scan_id INTEGER,
                FOREIGN KEY (scan_id) REFERENCES scans(id)
            )
        """)
        
        # Live hosts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS live_hosts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                subdomain TEXT NOT NULL,
                status_code INTEGER,
                title TEXT,
                tech_stack TEXT,
                content_length INTEGER,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scan_id INTEGER,
                FOREIGN KEY (scan_id) REFERENCES scans(id)
            )
        """)
        
        # URLs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                host TEXT NOT NULL,
                path TEXT,
                method TEXT DEFAULT 'GET',
                status_code INTEGER,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scan_id INTEGER,
                FOREIGN KEY (scan_id) REFERENCES scans(id)
            )
        """)
        
        # JS files table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS js_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                hash TEXT,
                size INTEGER,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_checked TIMESTAMP,
                changed BOOLEAN DEFAULT 0,
                scan_id INTEGER,
                FOREIGN KEY (scan_id) REFERENCES scans(id)
            )
        """)
        
        # Vulnerabilities table (for future use)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vulnerabilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                vulnerability_type TEXT NOT NULL,
                severity TEXT,
                description TEXT,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scan_id INTEGER,
                FOREIGN KEY (scan_id) REFERENCES scans(id)
            )
        """)
        
        # Create indexes for better query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subdomains_domain ON subdomains(domain)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_live_hosts_subdomain ON live_hosts(subdomain)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_urls_host ON urls(host)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scans_domain ON scans(domain)")
        
        conn.commit()

# ==================== Scan Operations ====================

def create_scan(domain, scan_type, tools=None):
    """Create a new scan record and return its ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        tools_str = json.dumps(tools) if tools else None
        cursor.execute("""
            INSERT INTO scans (domain, scan_type, status, tools)
            VALUES (?, ?, ?, ?)
        """, (domain, scan_type, 'Running', tools_str))
        return cursor.lastrowid

def update_scan_status(scan_id, status, error_message=None):
    """Update scan status."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE scans 
            SET status = ?, end_time = ?, error_message = ?
            WHERE id = ?
        """, (status, datetime.now(), error_message, scan_id))

def get_scan(scan_id):
    """Get scan details by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scans WHERE id = ?", (scan_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_all_scans(limit=100, offset=0):
    """Get all scans with pagination."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM scans 
            ORDER BY start_time DESC 
            LIMIT ? OFFSET ?
        """, (limit, offset))
        return [dict(row) for row in cursor.fetchall()]

def get_scans_by_domain(domain):
    """Get all scans for a specific domain."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM scans 
            WHERE domain = ? 
            ORDER BY start_time DESC
        """, (domain,))
        return [dict(row) for row in cursor.fetchall()]

def delete_scan(scan_id):
    """Delete a scan and all its associated data."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Delete associated data first (due to foreign key constraints)
        cursor.execute("DELETE FROM subdomains WHERE scan_id = ?", (scan_id,))
        cursor.execute("DELETE FROM live_hosts WHERE scan_id = ?", (scan_id,))
        cursor.execute("DELETE FROM urls WHERE scan_id = ?", (scan_id,))
        cursor.execute("DELETE FROM js_files WHERE scan_id = ?", (scan_id,))
        cursor.execute("DELETE FROM vulnerabilities WHERE scan_id = ?", (scan_id,))
        
        # Delete the scan itself
        cursor.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
        
        conn.commit()
        return True

# ==================== Subdomain Operations ====================

def add_subdomains(subdomains, domain, scan_id, source="discovery"):
    """Add multiple subdomains, return list of newly added ones."""
    new_subdomains = []
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for subdomain in subdomains:
            try:
                cursor.execute("""
                    INSERT INTO subdomains (subdomain, domain, source, scan_id)
                    VALUES (?, ?, ?, ?)
                """, (subdomain, domain, source, scan_id))
                new_subdomains.append(subdomain)
            except sqlite3.IntegrityError:
                # Subdomain already exists, skip
                pass
    return new_subdomains

def get_all_subdomains(domain=None):
    """Get all subdomains, optionally filtered by domain."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if domain:
            cursor.execute("SELECT subdomain FROM subdomains WHERE domain = ?", (domain,))
        else:
            cursor.execute("SELECT subdomain FROM subdomains")
        return [row['subdomain'] for row in cursor.fetchall()]

def get_subdomains_by_scan(scan_id):
    """Get subdomains discovered in a specific scan."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subdomains WHERE scan_id = ?", (scan_id,))
        return [dict(row) for row in cursor.fetchall()]

# ==================== Live Host Operations ====================

def add_live_hosts(hosts_data, scan_id):
    """Add multiple live hosts."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for host in hosts_data:
            try:
                cursor.execute("""
                    INSERT INTO live_hosts 
                    (url, subdomain, status_code, title, tech_stack, content_length, scan_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    host.get('url'),
                    host.get('subdomain'),
                    host.get('status_code'),
                    host.get('title'),
                    json.dumps(host.get('tech_stack')) if host.get('tech_stack') else None,
                    host.get('content_length'),
                    scan_id
                ))
            except sqlite3.IntegrityError:
                # Host already exists, skip
                pass

def get_live_hosts(scan_id=None):
    """Get live hosts, optionally filtered by scan."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if scan_id:
            cursor.execute("SELECT * FROM live_hosts WHERE scan_id = ?", (scan_id,))
        else:
            cursor.execute("SELECT * FROM live_hosts")
        return [dict(row) for row in cursor.fetchall()]

# ==================== URL Operations ====================

def add_urls(urls_data, scan_id):
    """Add multiple URLs."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for url_info in urls_data:
            try:
                cursor.execute("""
                    INSERT INTO urls (url, host, path, method, status_code, scan_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    url_info.get('url'),
                    url_info.get('host'),
                    url_info.get('path'),
                    url_info.get('method', 'GET'),
                    url_info.get('status_code'),
                    scan_id
                ))
            except sqlite3.IntegrityError:
                # URL already exists, skip
                pass

def get_urls(scan_id=None, host=None):
    """Get URLs, optionally filtered by scan or host."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if scan_id:
            cursor.execute("SELECT * FROM urls WHERE scan_id = ?", (scan_id,))
        elif host:
            cursor.execute("SELECT * FROM urls WHERE host = ?", (host,))
        else:
            cursor.execute("SELECT * FROM urls")
        return [dict(row) for row in cursor.fetchall()]

# ==================== JS File Operations ====================

def add_js_files(js_files_data, scan_id):
    """Add or update JS files."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for js_file in js_files_data:
            try:
                cursor.execute("""
                    INSERT INTO js_files (url, hash, size, scan_id)
                    VALUES (?, ?, ?, ?)
                """, (
                    js_file.get('url'),
                    js_file.get('hash'),
                    js_file.get('size'),
                    scan_id
                ))
            except sqlite3.IntegrityError:
                # JS file exists, check if hash changed
                cursor.execute("SELECT hash FROM js_files WHERE url = ?", (js_file.get('url'),))
                row = cursor.fetchone()
                if row and row['hash'] != js_file.get('hash'):
                    cursor.execute("""
                        UPDATE js_files 
                        SET hash = ?, last_checked = ?, changed = 1
                        WHERE url = ?
                    """, (js_file.get('hash'), datetime.now(), js_file.get('url')))

def get_js_files(scan_id=None, changed_only=False):
    """Get JS files, optionally filtered by scan or changed status."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if scan_id:
            cursor.execute("SELECT * FROM js_files WHERE scan_id = ?", (scan_id,))
        elif changed_only:
            cursor.execute("SELECT * FROM js_files WHERE changed = 1")
        else:
            cursor.execute("SELECT * FROM js_files")
        return [dict(row) for row in cursor.fetchall()]

# ==================== Migration from JSON ====================

def migrate_from_json():
    """Migrate existing JSON data to SQLite database."""
    if not os.path.exists(DB_FILE):
        print("[*] No existing JSON database found. Skipping migration.")
        return
    
    try:
        with open(DB_FILE, 'r') as f:
            data = json.load(f)
        
        print("[*] Migrating data from JSON to SQLite...")
        
        # Create a migration scan
        scan_id = create_scan("migration", "migration", ["json_import"])
        
        # Migrate subdomains
        if data.get('subdomains'):
            print(f"[*] Migrating {len(data['subdomains'])} subdomains...")
            for subdomain in data['subdomains']:
                # Extract domain from subdomain
                parts = subdomain.split('.')
                domain = '.'.join(parts[-2:]) if len(parts) >= 2 else subdomain
                add_subdomains([subdomain], domain, scan_id, "json_migration")
        
        # Migrate live hosts
        if data.get('live_hosts'):
            print(f"[*] Migrating {len(data['live_hosts'])} live hosts...")
            hosts_data = [{'url': host, 'subdomain': host} for host in data['live_hosts']]
            add_live_hosts(hosts_data, scan_id)
        
        # Migrate JS files
        if data.get('js_files'):
            print(f"[*] Migrating {len(data['js_files'])} JS files...")
            js_data = [{'url': url, 'hash': hash_val} for url, hash_val in data['js_files'].items()]
            add_js_files(js_data, scan_id)
        
        update_scan_status(scan_id, 'Completed')
        
        # Backup original JSON file
        backup_file = DB_FILE + '.backup'
        os.rename(DB_FILE, backup_file)
        print(f"[+] Migration complete! Original JSON backed up to {backup_file}")
        
    except Exception as e:
        print(f"[-] Migration failed: {e}")

# ==================== Statistics ====================

def get_scan_statistics(scan_id):
    """Get statistics for a specific scan."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        stats = {}
        
        # Count subdomains
        cursor.execute("SELECT COUNT(*) as count FROM subdomains WHERE scan_id = ?", (scan_id,))
        stats['subdomains_count'] = cursor.fetchone()['count']
        
        # Count live hosts
        cursor.execute("SELECT COUNT(*) as count FROM live_hosts WHERE scan_id = ?", (scan_id,))
        stats['live_hosts_count'] = cursor.fetchone()['count']
        
        # Count URLs
        cursor.execute("SELECT COUNT(*) as count FROM urls WHERE scan_id = ?", (scan_id,))
        stats['urls_count'] = cursor.fetchone()['count']
        
        # Count JS files
        cursor.execute("SELECT COUNT(*) as count FROM js_files WHERE scan_id = ?", (scan_id,))
        stats['js_files_count'] = cursor.fetchone()['count']
        
        return stats

# Initialize database on module import
if __name__ == "__main__":
    init_db()
    print("[+] Database initialized successfully!")
    migrate_from_json()
