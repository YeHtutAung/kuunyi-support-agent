import os
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

print(f"API Key: {GEMINI_API_KEY[:20]}...")

response = requests.post(
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
    json={
        "contents": [{
            "parts": [{
                "text": "What is 2+2?"
            }]
        }]
    },
    params={"key": GEMINI_API_KEY},
    headers={"Content-Type": "application/json"}
)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")