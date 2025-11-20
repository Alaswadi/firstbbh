import subprocess
import os
import requests
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import TOOLS, JS_DIR, ENABLE_MULTITHREADING, MAX_WORKERS

def run_gau(domain, output_file):
    """Runs gau to fetch known URLs."""
    cmd = [
        TOOLS["gau"],
        domain,
        "--o", output_file
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                return [line.strip() for line in f if line.strip()]
    except subprocess.CalledProcessError as e:
        print(f"Error running gau: {e}")
    except FileNotFoundError:
        print("gau not found.")
    return []

def download_js(url):
    """Downloads a JS file and returns its content and hash."""
    try:
        response = requests.get(url, timeout=10, verify=False)
        if response.status_code == 200:
            content = response.text
            file_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            return content, file_hash
    except Exception as e:
        print(f"Failed to download JS {url}: {e}")
    return None, None

def save_js_file(filename, content):
    """Saves JS content to a file."""
    path = os.path.join(JS_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return path

def run_gau_parallel(hosts, output_dir):
    """
    Runs gau on multiple hosts in parallel.
    Returns aggregated list of URLs.
    """
    if not hosts:
        return []
    
    if not ENABLE_MULTITHREADING or len(hosts) <= 1:
        # Sequential execution for single host or if multithreading disabled
        all_urls = []
        for host in hosts:
            temp_file = os.path.join(output_dir, f"temp_gau_{hash(host)}.txt")
            urls = run_gau(host, temp_file)
            all_urls.extend(urls)
            if os.path.exists(temp_file):
                os.remove(temp_file)
        return list(set(all_urls))
    
    # Parallel execution
    print(f"[*] Running gau on {len(hosts)} hosts in parallel...")
    all_urls = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_host = {}
        
        for host in hosts:
            temp_file = os.path.join(output_dir, f"temp_gau_{hash(host)}.txt")
            future = executor.submit(run_gau, host, temp_file)
            future_to_host[future] = (host, temp_file)
        
        # Collect results
        for future in as_completed(future_to_host):
            host, temp_file = future_to_host[future]
            try:
                result = future.result()
                print(f"[+] Found {len(result)} URLs from {host}")
                all_urls.extend(result)
            except Exception as e:
                print(f"[-] Failed to gather URLs from {host}: {e}")
            finally:
                # Clean up temp file
                if os.path.exists(temp_file):
                    os.remove(temp_file)
    
    # Deduplicate and return
    unique_urls = list(set(all_urls))
    print(f"[+] Total unique URLs found: {len(unique_urls)}")
    return unique_urls
