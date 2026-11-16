import os
from pathlib import Path
from dotenv import load_dotenv

# Search for .env in current directory, smart_rx folder, and project root
_curr_dir = Path(__file__).resolve().parent
for _p in [Path.cwd() / ".env", _curr_dir.parent / ".env", _curr_dir.parent.parent / ".env"]:
    if _p.exists():
        load_dotenv(_p, override=False)

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "smart_rx_yuvraj_2026_secret_key")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "mysql+pymysql://smart_rx_app:SmartRx2026Db@localhost/smart_rx"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_TIME_LIMIT = 3600
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

