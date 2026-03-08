import google.generativeai as genai
from config import settings
import os
# lowercase attribute as defined in config.py
genai.configure(api_key=settings.gemini_api_key)
print("Listing available models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error: {e}")
