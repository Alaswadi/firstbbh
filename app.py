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
    get_open_ports,
    migrate_from_json,
    delete_scan
)

app = Flask(__name__)

# Add JSON parsing filter for templates
import json as json_module
@app.template_filter('from_json')
def from_json_filter(value):
    """Parse JSON string to Python object."""
    if not value:
        return []
    try:
        return json_module.loads(value)
    except:
        return []

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
        scan_type = request.form.get('scan_type', 'standard')
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
    subdomains = get_subdomains_by_scan(scan_id)[:100]
    live_hosts = get_live_hosts(scan_id)[:100]
    urls = get_urls(scan_id)[:100]
    open_ports = get_open_ports(scan_id)[:100]
    
    # Parse tools from JSON string
    if scan.get('tools'):
        try:
            scan['tools'] = json.loads(scan['tools'])
        except:
            scan['tools'] = []
    
    return render_template('results.html', 
                         scan=scan, 
                         stats=stats,
                         subdomains=subdomains,
                         live_hosts=live_hosts,
                         urls=urls,
                         open_ports=open_ports)

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

@app.route('/scan/<int:scan_id>/delete', methods=['POST'])
def delete_scan_route(scan_id):
    """Delete a scan and redirect to home."""
    try:
        delete_scan(scan_id)
        return redirect(url_for('index'))
    except Exception as e:
        return f"Error deleting scan: {e}", 500

@app.route('/api/scan/<int:scan_id>/run-tool', methods=['POST'])
def run_tool_on_hosts(scan_id):
    """Run GAU or Nuclei on selected hosts."""
    try:
        data = request.get_json()
        tool = data.get('tool')
        hosts = data.get('hosts', [])
        
        if not tool or not hosts:
            return jsonify({'success': False, 'error': 'Missing tool or hosts'}), 400
        
        if tool not in ['gau', 'nuclei']:
            return jsonify({'success': False, 'error': 'Invalid tool'}), 400
        
        # Run the tool in a background thread
        def run_tool_background():
            import os
            from modules.content import run_gau
            
            scan = get_scan(scan_id)
            if not scan:
                return
            
            domain = scan['domain']
            output_dir = os.path.join('output', domain)
            os.makedirs(output_dir, exist_ok=True)
            
            if tool == 'gau':
                # Run GAU on selected hosts
                from modules.content import run_gau_parallel
                urls = run_gau_parallel(hosts, output_dir)
                
                # Store URLs in database
                if urls:
                    from database import add_urls
                    from urllib.parse import urlparse
                    urls_data = []
                    for url in urls:
                        try:
                            parsed = urlparse(url)
                            urls_data.append({
                                'url': url,
                                'host': parsed.netloc,
                                'path': parsed.path
                            })
                        except:
                            pass
                    if urls_data:
                        add_urls(urls_data, scan_id)
                        
            elif tool == 'nuclei':
                # Run Nuclei on selected hosts
                hosts_file = os.path.join(output_dir, 'selected_hosts.txt')
                with open(hosts_file, 'w') as f:
                    for host in hosts:
                        f.write(f"{host}\n")
                
                # Note: Nuclei integration would go here
                # For now, just log that it would run
                print(f"[*] Would run Nuclei on {len(hosts)} hosts")
        
        import threading
        thread = threading.Thread(target=run_tool_background)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': f'{tool.upper()} scan started on {len(hosts)} host(s). Results will appear shortly.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # Listen on 0.0.0.0 to allow external access (e.g., from VPS)
    # Use debug=False for production deployment
    app.run(debug=False, port=5050, host='0.0.0.0')
