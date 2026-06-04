import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load configuration parameters
load_dotenv(dotenv_path=BASE_DIR / ".env")

class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "llama-3.2-90b-vision-preview")
    
    OUTPUT_DIR = BASE_DIR / os.getenv("OUTPUT_DIR", "output")
    TEMP_DIR = BASE_DIR / os.getenv("TEMP_DIR", "temp")
    LOGS_DIR = BASE_DIR / os.getenv("LOGS_DIR", "logs")

    @classmethod
    def validate(cls):
        """Verifies directory structures and active Groq credentials."""
        if not cls.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is missing from the .env configuration. "
                "Please add a valid Groq API key to run this tool."
            )
            
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)