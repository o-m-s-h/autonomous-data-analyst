import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL")

UPLOAD_DIR = os.getenv(
    "UPLOAD_DIR",
    "data/uploads"
)