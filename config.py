import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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

# Flask Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Database Configuration (PostgreSQL)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "bbh_automation")
DB_USER = os.getenv("DB_USER", "bbh_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

# Database connection string
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Legacy SQLite path (for migration)
DB_FILE = os.path.join(DATA_DIR, "assets.json")  # Legacy JSON storage
SQLITE_DB_PATH = os.path.join(DATA_DIR, "bbh_automation.db")  # SQLite database

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_URL = os.getenv("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")

# Celery Configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", f"redis://{REDIS_HOST}:{REDIS_PORT}/1")

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

# Multithreading Configuration
ENABLE_MULTITHREADING = True
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "5"))  # Number of threads for parallel execution
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))  # Batch size for chunked processing

# Celery Task Configuration
CELERY_TASK_SOFT_TIME_LIMIT = 3600  # 1 hour soft limit
CELERY_TASK_TIME_LIMIT = 7200  # 2 hour hard limit
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_SEND_SENT_EVENT = True
