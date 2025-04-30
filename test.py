# test_groq_api.py
import os
from dotenv import load_dotenv
import groq

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
print(f"GROQ_API_KEY: {'Set' if api_key else 'Not Set'}")
client = groq.Groq(api_key=api_key)
response = client.chat.completions.create(
    model="llama3-70b-8192",
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.choices[0].message.content)