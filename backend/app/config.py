import os
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent

# The documented command runs from backend/, while the checked-in local .env is
# kept at the project root. Resolve both explicitly so credentials/model settings
# do not depend on the shell's current directory.
load_dotenv(PROJECT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")

UPLOAD_DIR = os.getenv(
    "UPLOAD_DIR",
    str(BACKEND_DIR / "data" / "uploads")
)
