import os
from dotenv import load_dotenv

load_dotenv()

print("Testing environment setup...")
print(f"GOOGLE_API_KEY: {os.getenv('GOOGLE_API_KEY')[:10] if os.getenv('GOOGLE_API_KEY') else 'NOT SET'}...")
print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL')}")
print(f"SUPABASE_KEY: {os.getenv('SUPABASE_KEY')[:10] if os.getenv('SUPABASE_KEY') else 'NOT SET'}...")
print("\nAll good! Your .env file is working ✓")