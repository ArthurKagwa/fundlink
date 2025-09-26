from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Configuration settings for the telbot_llm module
class Config:
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
    INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")
    TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY", "your_together_api_key_here")
    TOGETHER_MODEL = os.getenv("TOGETHER_MODEL", "meta-llama/Llama-3.1-70B-Instruct-Turbo")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.2))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")