import subprocess
import os
import requests
import hashlib
from config import TOOLS, JS_DIR

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
