import os
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

# List available models
response = requests.get(
    f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}",
    headers={"Content-Type": "application/json"}
)

print(f"Status: {response.status_code}")
print(f"\nAvailable Models:")
data = response.json()
if "models" in data:
    for model in data["models"]:
        print(f"  - {model['name']}")
else:
    print(response.text)