from flask import Flask, render_template, request, redirect, url_for, jsonify
import threading
import os
import json
from main import run_scan
from config import OUTPUT_DIR
from database import (
    init_db,
    get_all_scans,
    get_scan,
    get_scan_statistics,
    get_subdomains_by_scan,
    get_live_hosts,
    get_urls,
    migrate_from_json
)

app = Flask(__name__)

# Initialize database
init_db()

# Try to migrate from JSON if it exists
try:
    migrate_from_json()
except Exception as e:
    print(f"Migration note: {e}")

@app.route('/')
def index():
    # Get recent scans from database with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    scans = get_all_scans(limit=per_page, offset=offset)
    
    # Add statistics to each scan
    for scan in scans:
        scan['stats'] = get_scan_statistics(scan['id'])
    
    return render_template('index.html', scans=scans, page=page)

@app.route('/scan/new', methods=['GET', 'POST'])
def new_scan():
    if request.method == 'POST':
        domain = request.form.get('domain')
        scan_type = request.form.get('scan_type', 'full')
        tools = request.form.getlist('tools')
        
        if not domain:
            return "Domain is required", 400
        
        # Start scan in background
        thread = threading.Thread(
            target=run_scan, 
            args=(domain, scan_type, tools)
        )
        thread.daemon = True
        thread.start()
        
        return redirect(url_for('index'))
        
    return render_template('new_scan.html')

@app.route('/results/<int:scan_id>')
def view_results(scan_id):
    scan = get_scan(scan_id)
    if not scan:
        return "Scan not found", 404
    
    # Get detailed results
    stats = get_scan_statistics(scan_id)
    subdomains = get_subdomains_by_scan(scan_id)
    live_hosts = get_live_hosts(scan_id)
    urls = get_urls(scan_id)
    
    # Parse tools from JSON string
    if scan.get('tools'):
        try:
            scan['tools'] = json.loads(scan['tools'])
        except:
            scan['tools'] = []
    
    return render_template('results.html', 
                         scan=scan, 
                         stats=stats,
                         subdomains=subdomains[:100],  # Limit display
                         live_hosts=live_hosts[:100],
                         urls=urls[:100])

@app.route('/api/scans')
def api_scans():
    """API endpoint to get all scans."""
    scans = get_all_scans(limit=100)
    return jsonify(scans)

@app.route('/api/scan/<int:scan_id>')
def api_scan(scan_id):
    """API endpoint to get specific scan details."""
    scan = get_scan(scan_id)
    if not scan:
        return jsonify({"error": "Scan not found"}), 404
    
    stats = get_scan_statistics(scan_id)
    scan['stats'] = stats
    return jsonify(scan)

@app.route('/api/scan/<int:scan_id>/subdomains')
def api_scan_subdomains(scan_id):
    """API endpoint to get subdomains from a scan."""
    subdomains = get_subdomains_by_scan(scan_id)
    return jsonify(subdomains)

@app.route('/api/scan/<int:scan_id>/live-hosts')
def api_scan_live_hosts(scan_id):
    """API endpoint to get live hosts from a scan."""
    live_hosts = get_live_hosts(scan_id)
    return jsonify(live_hosts)

@app.route('/api/scan/<int:scan_id>/urls')
def api_scan_urls(scan_id):
    """API endpoint to get URLs from a scan."""
    urls = get_urls(scan_id)
    return jsonify(urls)

if __name__ == '__main__':
    # Listen on 0.0.0.0 to allow external access (e.g., from VPS)
    app.run(debug=True, port=5050, host='0.0.0.0')

