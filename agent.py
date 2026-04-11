"""
KuuNyi Support Agent - With Gemini 2.5 Flash AI
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def call_gemini(user_message: str) -> str:
    """Call Gemini 2.5 Flash API to generate response"""
    
    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
            json={
                "contents": [{
                    "parts": [{
                        "text": f"""You are a friendly KuuNyi customer support agent for an enrollment platform.
Help customers with questions about:
- Enrollment process
- Payment methods (MMQR, bank transfer)
- Status checking
- JLPT levels (N5, N4, N3, N2, N1)
- Refunds and policies

Customer question: {user_message}

Respond helpfully with emoji and clear formatting. Keep responses concise and friendly."""
                    }]
                }]
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and len(data["candidates"]) > 0:
                return data["candidates"][0]["content"]["parts"][0]["text"]
        
        return f"Error: {response.status_code} - {response.text[:100]}"
    
    except requests.exceptions.Timeout:
        return "Request timed out. Please try again."
    except Exception as e:
        return f"Error: {str(e)}"


print("\n" + "="*70)
print("🎯 KuuNyi Smart Customer Support Agent")
print("Powered by Gemini 2.5 Flash AI")
print("="*70)
print("\n✅ Agent is ready! Ask me about:")
print("   • JLPT levels")
print("   • How to pay")
print("   • Enrollment process")
print("   • Checking your status")
print("   • Refund policy")
print("\nType 'quit' to exit\n")

while True:
    try:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("\nAgent: Goodbye! Have a great day! 👋\n")
            break
        
        if not user_input:
            continue
        
        print("\nAgent: ", end="", flush=True)
        response = call_gemini(user_input)
        print(response)
        print()
    
    except KeyboardInterrupt:
        print("\n\nAgent: Goodbye! 👋\n")
        break
    except Exception as e:
        print(f"\nError: {e}\n")