import argparse
import os
from config import OUTPUT_DIR
from modules.discovery import run_discovery
from modules.storage import update_subdomains
from modules.monitoring import process_new_subdomains, monitor_js
from modules.probing import run_httpx
from modules.content import run_gau

def main():
    parser = argparse.ArgumentParser(description="Bug Bounty Automation - Phase 1")
    parser.add_argument("-d", "--domain", required=True, help="Target domain (e.g., example.com)")
    args = parser.parse_args()
    
    domain = args.domain
    domain_output_dir = os.path.join(OUTPUT_DIR, domain)
    os.makedirs(domain_output_dir, exist_ok=True)
    
    print(f"[*] Starting automation for: {domain}")
    
    # 1. Discovery
    print("[*] Running Subdomain Discovery...")
    found_subdomains = run_discovery(domain, domain_output_dir)
    
    # 2. Diffing / Storage Update
    print("[*] Checking for new subdomains...")
    new_subdomains = update_subdomains(found_subdomains)
    
    if new_subdomains:
        print(f"[+] Found {len(new_subdomains)} new subdomains.")
        process_new_subdomains(new_subdomains)
        
        # Save new subdomains to a file for probing
        new_subs_file = os.path.join(domain_output_dir, "new_subdomains.txt")
        with open(new_subs_file, 'w') as f:
            for sub in new_subdomains:
                f.write(f"{sub}\n")
        
        # 3. Probing (only on new assets for efficiency)
        print("[*] Probing new assets for web servers...")
        live_hosts_file = os.path.join(domain_output_dir, "live_hosts.txt")
        live_hosts = run_httpx(new_subs_file, live_hosts_file)
        print(f"[+] Found {len(live_hosts)} live hosts.")
        
        # 4. Content Discovery & JS Monitoring
        print("[*] Gathering URLs and JS files...")
        all_js_urls = []
        for host in live_hosts:
            # Strip protocol for gau if needed, or keep it. Gau usually takes domain.
            # But here we might want to run gau on the specific host if it's a subdomain
            # For now, let's just run gau on the main domain once, but that might be too broad.
            # Better: run gau on the new live subdomains.
            
            host_clean = host.replace("http://", "").replace("https://", "")
            gau_out = os.path.join(domain_output_dir, f"{host_clean}_urls.txt")
            urls = run_gau(host_clean, gau_out)
            
            # Filter for JS files
            js_urls = [u for u in urls if u.endswith(".js")]
            all_js_urls.extend(js_urls)
            
        # 5. JS Monitoring
        if all_js_urls:
            print(f"[*] Monitoring {len(all_js_urls)} JS files...")
            monitor_js(list(set(all_js_urls)))
            
    else:
        print("[-] No new subdomains found.")

    print("[*] Scan completed.")

if __name__ == "__main__":
    main()
