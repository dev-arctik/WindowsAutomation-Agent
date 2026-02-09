"""
API key loading from .env file.

Loads environment variables from the project root .env file.
Raises ValueError if required keys are missing.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY not found in .env file. "
        f"Please create {ENV_PATH} with your API key."
    )


if __name__ == "__main__":
    print(f"Loaded API key from: {ENV_PATH}")
    print(f"OPENAI_API_KEY: {OPENAI_API_KEY[:8]}...{OPENAI_API_KEY[-4:]}")
