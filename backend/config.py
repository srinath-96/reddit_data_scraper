# backend/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file in the project root
# Assumes .env is in the parent directory of 'backend'
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
print(f"Attempting to load .env file from: {dotenv_path}")
if os.path.exists(dotenv_path):
    if load_dotenv(dotenv_path=dotenv_path):
        print(".env file loaded successfully.")
    else:
        print("Warning: .env file found but may be empty or failed to load.")
else:
    print("Warning: .env file not found at expected location. Relying on system environment variables.")


# --- Google API Key ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("WARNING: GOOGLE_API_KEY not found in environment variables or .env file.")

# --- Reddit API Credentials ---
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT]):
     print("WARNING: One or more Reddit API credentials (ID, SECRET, USER_AGENT) not found.")

# --- ADK / App Configuration ---
# You can set defaults here if they are not in the .env file
ADK_MODEL_STRING = os.getenv("ADK_MODEL_STRING", "gemini-2.0-flash") # Default if not set
APP_NAME = os.getenv("APP_NAME", "RedditScraperApp")
USER_ID = os.getenv("USER_ID", "default_user")

# Optional: Set environment variable for GenAI SDK if needed
# os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"

print("Configuration loading complete.")
# Add checks here if keys are critical
if not GOOGLE_API_KEY:
    print("!!! CRITICAL WARNING: GOOGLE_API_KEY is missing. ADK Agent will likely fail. !!!")
if not REDDIT_CLIENT_ID:
    print("!!! CRITICAL WARNING: REDDIT_CLIENT_ID is missing. Reddit connection will fail. !!!")