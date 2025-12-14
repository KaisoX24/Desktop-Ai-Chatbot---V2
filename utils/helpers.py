import os
import sys
from dotenv import load_dotenv

def resource_path(relative_path: str) -> str:
    """Return path adjusted for PyInstaller (_MEIPASS2) or normal execution."""
    try:
        base_path = sys._MEIPASS2
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Safe load .env
def load_env():
    env_path = resource_path("assets/.env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        load_dotenv()
    return os.getenv("GROQ_API_KEY")