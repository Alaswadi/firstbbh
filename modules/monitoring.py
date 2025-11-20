import os
from modules.storage import load_data, save_data
from modules.alerting import send_alert
from modules.content import download_js, save_js_file

def process_new_subdomains(new_subs):
    """
    Processes newly discovered subdomains.
    """
    if not new_subs:
        return

    send_alert(f"Found {len(new_subs)} new subdomains!", severity="medium", details={"subdomains": new_subs})
    # Here we would trigger further scanning (probing) on these new subs

def monitor_js(js_urls):
    """
    Monitors JS files for changes.
    """
    data = load_data()
    stored_js = data.get("js_files", {})
    
    for url in js_urls:
        filename = url.split('/')[-1] or "unknown.js"
        # Sanitize filename
        filename = "".join([c for c in filename if c.isalnum() or c in "._-"])
        
        content, file_hash = download_js(url)
        if not content:
            continue
            
        if url not in stored_js:
            # New JS file
            send_alert(f"New JS file found: {url}", severity="low")
            save_js_file(f"{file_hash}_{filename}", content)
            stored_js[url] = file_hash
        elif stored_js[url] != file_hash:
            # Changed JS file
            send_alert(f"JS file changed: {url}", severity="high")
            # Save new version
            save_js_file(f"{file_hash}_{filename}", content)
            # TODO: Implement diffing logic here (compare with old file)
            stored_js[url] = file_hash
            
    data["js_files"] = stored_js
    save_data(data)
