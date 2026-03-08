import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
load_dotenv()

class Settings(BaseSettings):
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    model_name: str = "gemini-2.0-flash"
    max_tokens: int = 512
    temperature: float = 0.1
    class Config:
        env_file = ".env"

settings = Settings()
