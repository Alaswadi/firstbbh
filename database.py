"""
PostgreSQL database layer for bug bounty automation.
Migrated from SQLite to PostgreSQL for production use.
"""
import psycopg2
from psycopg2 import pool, extras
import json
import os
from datetime import datetime
from contextlib import contextmanager
from config import DATABASE_URL, DATA_DIR, SQLITE_DB_PATH, DB_FILE

# Connection pool for better performance
connection_pool = None

def init_connection_pool():
    """Initialize PostgreSQL connection pool."""
    global connection_pool
    if connection_pool is None:
        try:
            connection_pool = psycopg2.pool.SimpleConnectionPool(
                1,  # minconn
                20,  # maxconn
                DATABASE_URL
            )
            print("[+] PostgreSQL connection pool created successfully")
        except Exception as e:
            print(f"[-] Error creating connection pool: {e}")
            raise

@contextmanager
def get_db_connection():
    """Context manager for database connections using connection pool."""
    global connection_pool
    
    if connection_pool is None:
        init_connection_pool()
    
    conn = connection_pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        connection_pool.putconn(conn)

def init_db():
    """Initialize the database schema for PostgreSQL."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Scans table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
                subdomain TEXT NOT NULL UNIQUE,
                domain TEXT NOT NULL,
                source TEXT,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scan_id INTEGER REFERENCES scans(id)
            )
        """)
        
        # Live hosts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS live_hosts (
                id SERIAL PRIMARY KEY,
                url TEXT NOT NULL UNIQUE,
                subdomain TEXT NOT NULL,
                status_code INTEGER,
                title TEXT,
                tech_stack TEXT,
                content_length INTEGER,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scan_id INTEGER REFERENCES scans(id)
            )
        """)
        
        # URLs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                id SERIAL PRIMARY KEY,
                url TEXT NOT NULL UNIQUE,
                host TEXT NOT NULL,
                path TEXT,
                method TEXT DEFAULT 'GET',
                status_code INTEGER,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scan_id INTEGER REFERENCES scans(id)
            )
        """)
        
        # JS files table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS js_files (
                id SERIAL PRIMARY KEY,
                url TEXT NOT NULL UNIQUE,
                hash TEXT,
                size INTEGER,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_checked TIMESTAMP,
                changed BOOLEAN DEFAULT FALSE,
                scan_id INTEGER REFERENCES scans(id)
            )
        """)
        
        # Open ports table (for Naabu results)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS open_ports (
                id SERIAL PRIMARY KEY,
                host TEXT NOT NULL,
                port INTEGER NOT NULL,
                protocol TEXT DEFAULT 'tcp',
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scan_id INTEGER REFERENCES scans(id),
                UNIQUE(host, port, scan_id)
            )
        """)
        
        # Vulnerabilities table (for future use)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vulnerabilities (
                id SERIAL PRIMARY KEY,
                url TEXT NOT NULL,
                vulnerability_type TEXT NOT NULL,
                severity TEXT,
                description TEXT,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scan_id INTEGER REFERENCES scans(id)
            )
        """)
        
        # Create indexes for better query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subdomains_domain ON subdomains(domain)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_live_hosts_subdomain ON live_hosts(subdomain)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_urls_host ON urls(host)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scans_domain ON scans(domain)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scans_status ON scans(status)")
        
        conn.commit()
        print("[+] Database schema initialized successfully")

# ==================== Scan Operations ====================

def create_scan(domain, scan_type, tools=None):
    """Create a new scan record and return its ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        tools_str = json.dumps(tools) if tools else None
        cursor.execute("""
            INSERT INTO scans (domain, scan_type, status, tools)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (domain, scan_type, 'Running', tools_str))
        scan_id = cursor.fetchone()[0]
        return scan_id

def update_scan_status(scan_id, status, error_message=None):
    """Update scan status."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE scans 
            SET status = %s, end_time = %s, error_message = %s
            WHERE id = %s
        """, (status, datetime.now(), error_message, scan_id))

def get_scan(scan_id):
    """Get scan details by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
        cursor.execute("SELECT * FROM scans WHERE id = %s", (scan_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_all_scans(limit=100, offset=0):
    """Get all scans with pagination."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
        cursor.execute("""
            SELECT * FROM scans 
            ORDER BY start_time DESC 
            LIMIT %s OFFSET %s
        """, (limit, offset))
        return [dict(row) for row in cursor.fetchall()]

def get_scans_by_domain(domain):
    """Get all scans for a specific domain."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
        cursor.execute("""
            SELECT * FROM scans 
            WHERE domain = %s 
            ORDER BY start_time DESC
        """, (domain,))
        return [dict(row) for row in cursor.fetchall()]

def delete_scan(scan_id):
    """Delete a scan and all its associated data."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # PostgreSQL will handle cascading deletes if we set up foreign keys properly
        # For now, delete manually
        cursor.execute("DELETE FROM subdomains WHERE scan_id = %s", (scan_id,))
        cursor.execute("DELETE FROM live_hosts WHERE scan_id = %s", (scan_id,))
        cursor.execute("DELETE FROM urls WHERE scan_id = %s", (scan_id,))
        cursor.execute("DELETE FROM js_files WHERE scan_id = %s", (scan_id,))
        cursor.execute("DELETE FROM open_ports WHERE scan_id = %s", (scan_id,))
        cursor.execute("DELETE FROM vulnerabilities WHERE scan_id = %s", (scan_id,))
        
        # Delete the scan itself
        cursor.execute("DELETE FROM scans WHERE id = %s", (scan_id,))
        
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
                    VALUES (%s, %s, %s, %s)
                """, (subdomain, domain, source, scan_id))
                new_subdomains.append(subdomain)
            except psycopg2.IntegrityError:
                # Subdomain already exists, skip
                conn.rollback()
                pass
    return new_subdomains

def get_all_subdomains(domain=None):
    """Get all subdomains, optionally filtered by domain."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if domain:
            cursor.execute("SELECT subdomain FROM subdomains WHERE domain = %s", (domain,))
        else:
            cursor.execute("SELECT subdomain FROM subdomains")
        return [row[0] for row in cursor.fetchall()]

def get_subdomains_by_scan(scan_id):
    """Get subdomains discovered in a specific scan."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
        cursor.execute("SELECT * FROM subdomains WHERE scan_id = %s", (scan_id,))
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
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    host.get('url'),
                    host.get('subdomain'),
                    host.get('status_code'),
                    host.get('title'),
                    host.get('tech_stack'),  # Already JSON string
                    host.get('content_length'),
                    scan_id
                ))
            except psycopg2.IntegrityError:
                # Host already exists, skip
                conn.rollback()
                pass

def get_live_hosts(scan_id=None):
    """Get live hosts, optionally filtered by scan."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
        if scan_id:
            cursor.execute("SELECT * FROM live_hosts WHERE scan_id = %s", (scan_id,))
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
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    url_info.get('url'),
                    url_info.get('host'),
                    url_info.get('path'),
                    url_info.get('method', 'GET'),
                    url_info.get('status_code'),
                    scan_id
                ))
            except psycopg2.IntegrityError:
                # URL already exists, skip
                conn.rollback()
                pass

def get_urls(scan_id=None, host=None):
    """Get URLs, optionally filtered by scan or host."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
        if scan_id:
            cursor.execute("SELECT * FROM urls WHERE scan_id = %s", (scan_id,))
        elif host:
            cursor.execute("SELECT * FROM urls WHERE host = %s", (host,))
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
                    VALUES (%s, %s, %s, %s)
                """, (
                    js_file.get('url'),
                    js_file.get('hash'),
                    js_file.get('size'),
                    scan_id
                ))
            except psycopg2.IntegrityError:
                # JS file exists, check if hash changed
                conn.rollback()
                cursor.execute("SELECT hash FROM js_files WHERE url = %s", (js_file.get('url'),))
                row = cursor.fetchone()
                if row and row[0] != js_file.get('hash'):
                    cursor.execute("""
                        UPDATE js_files 
                        SET hash = %s, last_checked = %s, changed = TRUE
                        WHERE url = %s
                    """, (js_file.get('hash'), datetime.now(), js_file.get('url')))

def get_js_files(scan_id=None, changed_only=False):
    """Get JS files, optionally filtered by scan or changed status."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
        if scan_id:
            cursor.execute("SELECT * FROM js_files WHERE scan_id = %s", (scan_id,))
        elif changed_only:
            cursor.execute("SELECT * FROM js_files WHERE changed = TRUE")
        else:
            cursor.execute("SELECT * FROM js_files")
        return [dict(row) for row in cursor.fetchall()]

# ==================== Open Ports Operations ====================

def add_open_ports(ports_data, scan_id):
    """Add multiple open ports from Naabu scan."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for port_info in ports_data:
            try:
                cursor.execute("""
                    INSERT INTO open_ports (host, port, protocol, scan_id)
                    VALUES (%s, %s, %s, %s)
                """, (
                    port_info.get('host'),
                    port_info.get('port'),
                    port_info.get('protocol', 'tcp'),
                    scan_id
                ))
            except psycopg2.IntegrityError:
                # Port already exists for this host in this scan, skip
                conn.rollback()
                pass

def get_open_ports(scan_id=None, host=None):
    """Get open ports, optionally filtered by scan or host."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
        if scan_id:
            cursor.execute("SELECT * FROM open_ports WHERE scan_id = %s", (scan_id,))
        elif host:
            cursor.execute("SELECT * FROM open_ports WHERE host = %s", (host,))
        else:
            cursor.execute("SELECT * FROM open_ports")
        return [dict(row) for row in cursor.fetchall()]

# ==================== Statistics ====================

def get_scan_statistics(scan_id):
    """Get statistics for a specific scan."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        stats = {}
        
        # Count subdomains
        cursor.execute("SELECT COUNT(*) FROM subdomains WHERE scan_id = %s", (scan_id,))
        stats['subdomains_count'] = cursor.fetchone()[0]
        
        # Count live hosts
        cursor.execute("SELECT COUNT(*) FROM live_hosts WHERE scan_id = %s", (scan_id,))
        stats['live_hosts_count'] = cursor.fetchone()[0]
        
        # Count URLs
        cursor.execute("SELECT COUNT(*) FROM urls WHERE scan_id = %s", (scan_id,))
        stats['urls_count'] = cursor.fetchone()[0]
        
        # Count JS files
        cursor.execute("SELECT COUNT(*) FROM js_files WHERE scan_id = %s", (scan_id,))
        stats['js_files_count'] = cursor.fetchone()[0]
        
        # Count open ports
        cursor.execute("SELECT COUNT(*) FROM open_ports WHERE scan_id = %s", (scan_id,))
        stats['open_ports_count'] = cursor.fetchone()[0]
        
        return stats

# ==================== Migration from SQLite ====================

def migrate_from_sqlite():
    """Migrate existing SQLite data to PostgreSQL database."""
    import sqlite3
    
    sqlite_path = SQLITE_DB_PATH
    
    if not os.path.exists(sqlite_path):
        print("[*] No existing SQLite database found. Skipping migration.")
        return
    
    try:
        # Connect to SQLite
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        print("[*] Migrating data from SQLite to PostgreSQL...")
        
        # Initialize PostgreSQL schema
        init_db()
        
        # Migrate scans
        sqlite_cursor.execute("SELECT * FROM scans")
        scans = sqlite_cursor.fetchall()
        
        if scans:
            print(f"[*] Migrating {len(scans)} scans...")
            with get_db_connection() as pg_conn:
                pg_cursor = pg_conn.cursor()
                for scan in scans:
                    pg_cursor.execute("""
                        INSERT INTO scans (id, domain, scan_type, status, start_time, end_time, tools, error_message)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                    """, (
                        scan['id'], scan['domain'], scan['scan_type'], scan['status'],
                        scan['start_time'], scan['end_time'], scan['tools'], scan['error_message']
                    ))
        
        # Migrate subdomains
        sqlite_cursor.execute("SELECT * FROM subdomains")
        subdomains = sqlite_cursor.fetchall()
        
        if subdomains:
            print(f"[*] Migrating {len(subdomains)} subdomains...")
            with get_db_connection() as pg_conn:
                pg_cursor = pg_conn.cursor()
                for subdomain in subdomains:
                    try:
                        pg_cursor.execute("""
                            INSERT INTO subdomains (subdomain, domain, source, discovered_at, scan_id)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            subdomain['subdomain'], subdomain['domain'], subdomain['source'],
                            subdomain['discovered_at'], subdomain['scan_id']
                        ))
                    except psycopg2.IntegrityError:
                        pg_conn.rollback()
        
        # Migrate live hosts
        sqlite_cursor.execute("SELECT * FROM live_hosts")
        live_hosts = sqlite_cursor.fetchall()
        
        if live_hosts:
            print(f"[*] Migrating {len(live_hosts)} live hosts...")
            with get_db_connection() as pg_conn:
                pg_cursor = pg_conn.cursor()
                for host in live_hosts:
                    try:
                        pg_cursor.execute("""
                            INSERT INTO live_hosts (url, subdomain, status_code, title, tech_stack, content_length, discovered_at, scan_id)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            host['url'], host['subdomain'], host['status_code'], host['title'],
                            host['tech_stack'], host['content_length'], host['discovered_at'], host['scan_id']
                        ))
                    except psycopg2.IntegrityError:
                        pg_conn.rollback()
        
        # Close SQLite connection
        sqlite_conn.close()
        
        # Backup original SQLite file
        backup_file = sqlite_path + '.backup'
        if not os.path.exists(backup_file):
            os.rename(sqlite_path, backup_file)
            print(f"[+] Migration complete! Original SQLite backed up to {backup_file}")
        else:
            print(f"[+] Migration complete! (Backup already exists)")
        
    except Exception as e:
        print(f"[-] Migration failed: {e}")
        raise

# Initialize connection pool on module import
try:
    init_connection_pool()
except Exception as e:
    print(f"[!] Warning: Could not initialize connection pool: {e}")
    print("[!] Database operations will fail until PostgreSQL is available")

if __name__ == "__main__":
    init_db()
    print("[+] Database initialized successfully!")
