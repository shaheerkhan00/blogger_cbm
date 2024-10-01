import os
from dotenv import load_dotenv
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import anthropic
import time
import html
import json

print("Starting script...")

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Access environment variables
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')

claude = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

try:
    response = claude.completions.create(
        model="claude-2.1",
        prompt=f"{anthropic.HUMAN_PROMPT} Hello, Claude! {anthropic.AI_PROMPT}",
        max_tokens_to_sample=100
    )
    print("API call successful. Response:", response.completion)
except anthropic.APIError as e:
    print(f"API Error: {e.status_code} - {e.message}")
except Exception as e:
    print(f"Unexpected error: {str(e)}")