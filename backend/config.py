import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
load_dotenv()

class Settings(BaseSettings):
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    # gemini-2.0-flash: stable & available on ALL free API keys.
    # The 10 RPM proactive limiter in main.py keeps us safely under
    # the free-tier 15 RPM cap — 429 errors are now prevented automatically.
    model_name: str = "gemini-2.0-flash"
    max_tokens: int = 512
    temperature: float = 0.1
    class Config:
        env_file = ".env"

settings = Settings()
