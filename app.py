from flask import Flask, render_template, request, redirect, url_for, jsonify
import threading
import os
import json
from main import run_scan
from config import OUTPUT_DIR

app = Flask(__name__)

# Store active scans in memory for now (in a real app, use a DB)
active_scans = {}
scan_history = []

@app.route('/')
def index():
    return render_template('index.html', scans=scan_history)

@app.route('/scan/new', methods=['GET', 'POST'])
def new_scan():
    if request.method == 'POST':
        domain = request.form.get('domain')
        scan_type = request.form.get('scan_type')
        tools = request.form.getlist('tools')
        
        if not domain:
            return "Domain is required", 400
            
        # Start scan in background
        scan_id = len(scan_history) + 1
        scan_info = {
            "id": scan_id,
            "domain": domain,
            "status": "Running",
            "type": scan_type,
            "tools": tools
        }
        scan_history.append(scan_info)
        
        thread = threading.Thread(target=run_scan_background, args=(scan_id, domain, scan_type, tools))
        thread.start()
        
        return redirect(url_for('index'))
        
    return render_template('new_scan.html')

def run_scan_background(scan_id, domain, scan_type, tools):
    try:
        # Find the scan in history and update status
        scan_record = next((s for s in scan_history if s['id'] == scan_id), None)
        if scan_record:
            results = run_scan(domain, scan_type=scan_type, tools=tools)
            scan_record['status'] = "Completed"
            scan_record['results'] = results
    except Exception as e:
        print(f"Scan failed: {e}")
        if scan_record:
            scan_record['status'] = "Failed"

@app.route('/results/<int:scan_id>')
def view_results(scan_id):
    scan = next((s for s in scan_history if s['id'] == scan_id), None)
    if not scan:
        return "Scan not found", 404
    return render_template('results.html', scan=scan)

@app.route('/api/scans')
def api_scans():
    return jsonify(scan_history)

if __name__ == '__main__':
    app.run(debug=True, port=5050)
