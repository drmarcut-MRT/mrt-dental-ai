import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    DATA_DIR = os.getenv("DATA_DIR", str(BASE_DIR / "data"))
    MEDIA_DIR = os.getenv("MEDIA_DIR", str(BASE_DIR / "media"))
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    FAL_KEY = os.getenv("FAL_KEY", "")
    AI_TEXT_MODEL = os.getenv("AI_TEXT_MODEL", "gpt-5.6-luna")
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024
