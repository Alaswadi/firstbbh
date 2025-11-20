import argparse
import os
from datetime import datetime
from config import OUTPUT_DIR
from modules.discovery import run_discovery
from modules.storage import update_subdomains
from modules.monitoring import process_new_subdomains, monitor_js
from modules.probing import run_httpx_batch
from modules.content import run_gau_parallel
from database import (
    init_db,
    create_scan,
    update_scan_status,
    add_subdomains,
    add_live_hosts,
    add_urls,
    add_js_files,
    get_scan_statistics
)

def run_scan(domain, scan_type="full", tools=None, scan_id=None):
    """
    Core scanning logic to be used by both CLI and Web App.
    Now integrated with database for persistent storage.
    """
    if tools is None:
        tools = ["subfinder", "amass", "naabu", "httpx", "gau", "nuclei"]  # Default all

    domain_output_dir = os.path.join(OUTPUT_DIR, domain)
    os.makedirs(domain_output_dir, exist_ok=True)
    
    print(f"[*] Starting automation for: {domain}")
    
    # Create scan record in database if not provided
    if scan_id is None:
        scan_id = create_scan(domain, scan_type, tools)
        print(f"[*] Scan ID: {scan_id}")
    
    # Initialize results container
    scan_results = {
        "scan_id": scan_id,
        "domain": domain,
        "new_subdomains": [],
        "live_hosts": [],
        "urls": []
    }

    try:
        # Standard workflow: Discovery → Probing → Port Scan
        print("[*] Running Subdomain Discovery...")
        
        # Always use subfinder for discovery
        found_subdomains = run_discovery(domain, domain_output_dir, ['subfinder'])
        
        # Store subdomains in database immediately
        print("[*] Storing subdomains in database...")
        new_subdomains = update_subdomains(found_subdomains, domain, scan_id)
        scan_results["new_subdomains"] = new_subdomains
        
        if found_subdomains:
            print(f"[+] Found {len(found_subdomains)} total subdomains ({len(new_subdomains)} new).")
            
            if new_subdomains:
                process_new_subdomains(new_subdomains)
            
            # Web server probing with HTTPX (before port scanning)
            print(f"[*] Probing {len(found_subdomains)} subdomains for web servers...")
            live_hosts_file = os.path.join(domain_output_dir, "live_hosts.txt")
            
            # Use batch processing with multithreading
            live_hosts_data = run_httpx_batch(found_subdomains, live_hosts_file)
            scan_results["live_hosts"] = [host.get('url') for host in live_hosts_data if host.get('url')]
            print(f"[+] Found {len(live_hosts_data)} live web servers.")
            
            # Store live hosts in database with detailed information
            if live_hosts_data:
                from database import add_live_hosts
                import json
                hosts_data = []
                for host_info in live_hosts_data:
                    url = host_info.get('url', '')
                    if url:
                        # Extract subdomain from URL
                        subdomain = url.replace('http://', '').replace('https://', '').split('/')[0]
                        hosts_data.append({
                            'url': url,
                            'subdomain': subdomain,
                            'status_code': host_info.get('status_code'),
                            'title': host_info.get('title', ''),
                            'tech_stack': json.dumps(host_info.get('tech', [])) if host_info.get('tech') else None,
                            'content_length': host_info.get('content_length', 0)
                        })
                add_live_hosts(hosts_data, scan_id)
            
            # Port scanning with Naabu (last step, important ports only)
            print(f"[*] Scanning important ports on {len(found_subdomains)} subdomains...")
            naabu_input = os.path.join(domain_output_dir, "subdomains.txt")
            naabu_output = os.path.join(domain_output_dir, "open_ports.txt")
            
            # Write subdomains to file for naabu
            with open(naabu_input, 'w') as f:
                for sub in found_subdomains:
                    f.write(f"{sub}\n")
            
            # Run naabu
            from modules.probing import run_naabu
            open_ports = run_naabu(naabu_input, naabu_output)
            print(f"[+] Found {len(open_ports)} hosts with open ports.")
            
            # Store open ports in database
            if open_ports:
                from database import add_open_ports
                ports_data = []
                for port_line in open_ports:
                    # Naabu output format: host:port or host:port [protocol]
                    try:
                        if ':' in port_line:
                            parts = port_line.split(':')
                            host = parts[0]
                            port_info = parts[1].split()[0]  # Get port number, ignore protocol if present
                            port = int(port_info)
                            ports_data.append({
                                'host': host,
                                'port': port,
                                'protocol': 'tcp'
                            })
                    except (ValueError, IndexError) as e:
                        print(f"[!] Could not parse port line: {port_line}")
                        continue
                
                if ports_data:
                    add_open_ports(ports_data, scan_id)
                    print(f"[+] Stored {len(ports_data)} open ports in database.")
        else:
            print("[-] No subdomains found.")
        
        # Update scan status to completed
        update_scan_status(scan_id, 'Completed')
        
        # Get and display statistics
        stats = get_scan_statistics(scan_id)
        print(f"\n[*] Scan Statistics:")
        print(f"    - Subdomains: {stats['subdomains_count']}")
        print(f"    - Live Hosts: {stats['live_hosts_count']}")
        print(f"    - URLs: {stats['urls_count']}")
        print(f"    - JS Files: {stats['js_files_count']}")
        
    except Exception as e:
        print(f"[-] Scan failed with error: {e}")
        update_scan_status(scan_id, 'Failed', str(e))
        raise
    
    print("[*] Scan completed.")
    return scan_results

def main():
    # Initialize database
    init_db()
    
    parser = argparse.ArgumentParser(description="Bug Bounty Automation - Phase 1")
    parser.add_argument("-d", "--domain", required=True, help="Target domain (e.g., example.com)")
    parser.add_argument("-t", "--type", default="full", help="Scan type: full, subdomain, probing")
    args = parser.parse_args()
    
    run_scan(args.domain, scan_type=args.type)

if __name__ == "__main__":
    main()
