"""Configuration module for ModelAdvisor backend."""
import os
from dotenv import load_dotenv

load_dotenv()

# Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required. Create a .env file with your API key.")
GEMINI_MODEL = "gemini-2.5-flash"

# Hugging Face Configuration
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")
HF_API_BASE = "https://huggingface.co/api"

# Session Configuration
SESSION_EXPIRY_HOURS = 24

# Cost Estimation Defaults (per hour)
COST_DEFAULTS = {
    "gpu_t4": 0.35,
    "gpu_a10": 1.10,
    "gpu_a100": 2.75,
    "gpu_rtx3090": 0.80,
    "api_openai_1k_tokens": 0.002,
    "api_gemini_1k_tokens": 0.00,  # Free tier
    "cloud_cpu_small": 0.05,
    "cloud_cpu_large": 0.15,
}
