import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Load .env file
load_dotenv(BASE_DIR / ".env")

# Telegram Bot Token (get from @BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# H143 Proxy API Configuration
H143_API_KEY = os.getenv("H143_API_KEY", "812F454A38C516C942C25120A09CB1F8").strip()
H143_API_URL = os.getenv("H143_API_URL", "https://h143.xyz/stats").strip()

# Admin Telegram ID (Only this ID has access to Admin Panel)
ADMIN_ID = int(os.getenv("ADMIN_ID", "8929349073").strip())

# Database path
DB_PATH = str(BASE_DIR / "bot_data.db")

# Supported Proxies list
SUPPORTED_PROXIES = ["H143Proxy"]
DEFAULT_PROXY = "H143Proxy"
