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
        # 1. Discovery
        if scan_type in ["full", "subdomain"]:
            print("[*] Running Subdomain Discovery...")
            found_subdomains = run_discovery(domain, domain_output_dir)
            
            # 2. Diffing / Storage Update
            print("[*] Checking for new subdomains...")
            new_subdomains = update_subdomains(found_subdomains, domain, scan_id)
            scan_results["new_subdomains"] = new_subdomains
            
            if new_subdomains:
                print(f"[+] Found {len(new_subdomains)} new subdomains.")
                process_new_subdomains(new_subdomains)
                
                # 3. Probing (only on new assets for efficiency)
                if scan_type in ["full", "probing"]:
                    print("[*] Probing new assets for web servers...")
                    live_hosts_file = os.path.join(domain_output_dir, "live_hosts.txt")
                    
                    # Use batch processing with multithreading
                    live_hosts = run_httpx_batch(new_subdomains, live_hosts_file)
                    scan_results["live_hosts"] = live_hosts
                    print(f"[+] Found {len(live_hosts)} live hosts.")
                    
                    # Store live hosts in database
                    if live_hosts:
                        hosts_data = []
                        for url in live_hosts:
                            # Extract subdomain from URL
                            subdomain = url.replace('http://', '').replace('https://', '').split('/')[0]
                            hosts_data.append({
                                'url': url,
                                'subdomain': subdomain
                            })
                        add_live_hosts(hosts_data, scan_id)
                    
                    # 4. Content Discovery & JS Monitoring
                    if scan_type == "full" and live_hosts:
                        print("[*] Gathering URLs and JS files...")
                        
                        # Use parallel URL gathering
                        all_urls = run_gau_parallel(live_hosts, domain_output_dir)
                        
                        # Save all URLs to file
                        all_urls_file = os.path.join(domain_output_dir, "all_urls.txt")
                        with open(all_urls_file, 'w') as f:
                            for url in all_urls:
                                f.write(f"{url}\n")
                        
                        scan_results["urls"] = all_urls
                        print(f"[+] Found {len(all_urls)} URLs. Saved to all_urls.txt")
                        
                        # Store URLs in database
                        if all_urls:
                            urls_data = []
                            for url in all_urls:
                                try:
                                    from urllib.parse import urlparse
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
                        
                        # Filter and monitor JS files
                        js_urls = [u for u in all_urls if u.endswith(".js")]
                        if js_urls:
                            print(f"[*] Monitoring {len(js_urls)} JS files...")
                            monitor_js(list(set(js_urls)))
                            
                            # Store JS files in database
                            js_data = [{'url': js_url} for js_url in js_urls]
                            add_js_files(js_data, scan_id)
            else:
                print("[-] No new subdomains found.")
        
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
