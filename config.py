"""Environment-backed API configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

API_KEYS = {
    "groq": os.getenv("GROQ_API_KEY"),
    "gemini": os.getenv("GEMINI_API_KEY"),
    "duffel": os.getenv("DUFFEL_API_KEY"),
    "serp": os.getenv("SERP_API_KEY"),
    "pexels": os.getenv("PEXELS_API_KEY"),
    "exchangerate": os.getenv("EXCHANGERATE_API_KEY"),
}

REQUIRED_KEYS = tuple(API_KEYS)

def validate_api_keys():
    missing = [name for name, value in API_KEYS.items() if not value]
    if missing:
        env_names = {
            "groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY",
            "duffel": "DUFFEL_API_KEY", "serp": "SERP_API_KEY",
            "pexels": "PEXELS_API_KEY",
            "exchangerate": "EXCHANGERATE_API_KEY",
        }
        raise RuntimeError(
            "Missing API keys in .env: " + ", ".join(env_names[k] for k in missing)
        )
    return API_KEYS
