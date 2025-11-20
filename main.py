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
        all_urls = []
        
        for host in live_hosts:
            # host is now just the URL (e.g., https://example.com) thanks to probing.py fix
            # We pass the domain/host to gau. 
            # gau accepts the URL or domain.
            
            # Clean host for display or other tools if needed, but gau handles URLs fine.
            # We won't write per-host files anymore.
            
            # For now, let's define a single output file for ALL URLs
            all_urls_file = os.path.join(domain_output_dir, "all_urls.txt")
            
            # We can run gau and append to the file? 
            # Or we can just run gau on the main domain? 
            # Running gau on every subdomain is better for coverage.
            
            # Let's use a temp file for each host to avoid the messy filename issue, then merge.
            temp_gau_file = os.path.join(domain_output_dir, "temp_gau.txt")
            urls = run_gau(host, temp_gau_file)
            all_urls.extend(urls)
            
            # Filter for JS files
            js_urls = [u for u in urls if u.endswith(".js")]
            all_js_urls.extend(js_urls)
            
            # Remove temp file
            if os.path.exists(temp_gau_file):
                os.remove(temp_gau_file)

        # Save all URLs to one file
        all_urls_file = os.path.join(domain_output_dir, "all_urls.txt")
        with open(all_urls_file, 'w') as f:
            for url in list(set(all_urls)):
                f.write(f"{url}\n")
        
        print(f"[+] Found {len(all_urls)} URLs. Saved to all_urls.txt")
            
        # 5. JS Monitoring
        if all_js_urls:
            print(f"[*] Monitoring {len(all_js_urls)} JS files...")
            monitor_js(list(set(all_js_urls)))
            
    else:
        print("[-] No new subdomains found.")

    print("[*] Scan completed.")

if __name__ == "__main__":
    main()
