import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
load_dotenv()

class Settings(BaseSettings):
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    # gemini-2.5-flash-lite: best free-tier limits (15 RPM, 1,000 RPD)
    # Do NOT change this to gemini-2.0-flash or gemini-2.5-flash — they have
    # far fewer free requests (10 RPM / 250 RPD).
    model_name: str = "gemini-2.5-flash-preview-04-17"
    max_tokens: int = 512
    temperature: float = 0.1
    class Config:
        env_file = ".env"

settings = Settings()
