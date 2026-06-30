import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file relative to this script
base_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(base_dir, ".env")
load_dotenv(dotenv_path, override=True)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_RAW = os.getenv("ADMIN_ID")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///bot.db")

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    print("XATOLIK: .env faylida BOT_TOKEN ko'rsatilmagan!", file=sys.stderr)
    print("Iltimos, .env faylini oching va bot tokenni yozing.", file=sys.stderr)
    # Don't exit immediately in case of testing, but define a fallback or warning
    BOT_TOKEN = None

try:
    ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW and ADMIN_ID_RAW != "YOUR_TELEGRAM_USER_ID_HERE" else None
except ValueError:
    print(f"XATOLIK: ADMIN_ID son bo'lishi kerak, lekin '{ADMIN_ID_RAW}' berildi!", file=sys.stderr)
    ADMIN_ID = None
