import os

# Project Root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Output Directories
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
JS_DIR = os.path.join(OUTPUT_DIR, "js_files")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(JS_DIR, exist_ok=True)

# Tool Paths (Assumes tools are in system PATH, otherwise specify absolute paths)
TOOLS = {
    "subfinder": "subfinder",
    "amass": "amass",
    "naabu": "naabu",
    "httpx": "httpx",
    "gau": "gau",
    "katana": "katana",
    "nuclei": "nuclei"
}

# Webhook URL for n8n or other alerting systems
WEBHOOK_URL = os.getenv("BBH_WEBHOOK_URL", "")

# Database File
DB_FILE = os.path.join(DATA_DIR, "assets.json")
