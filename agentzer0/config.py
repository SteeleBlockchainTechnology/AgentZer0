"""
Configuration settings for the AgentZer0 bot.
Load environment variables from .env file.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
import os.path
# Get the absolute path to the .env file in the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=env_path)

# Discord bot configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_PREFIX = os.getenv("DISCORD_PREFIX", "!")

# LLM configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3-8b-8192")

# System configuration
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"