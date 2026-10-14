
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE, override=True)

STORAGE_DIR = BASE_DIR / "storage"

MAX_VIDEO_SIZE = 700 * 1024 * 1024
MAX_AUDIO_SIZE = 24 * 1024 * 1024

ALLOWED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
    ".m4v",
}

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TRANSCRIPTION_MODEL = "whisper-large-v3-turbo"
TEXT_MODEL = "openai/gpt-oss-20b"

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
