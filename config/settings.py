# ============================================================================
# APPLICATION SETTINGS
# ============================================================================
# This file defines the configuration settings for the AgentZer0 application.
# It loads environment variables and provides them as typed settings objects.
# These settings are used throughout the application to configure behavior.
# Includes settings for both the API and Discord bot.

from pydantic_settings import BaseSettings  # For typed settings with validation
from dotenv import load_dotenv              # For loading environment variables from .env file

# Load environment variables from .env file if present
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables
    
    This class defines the configuration settings for the application.
    Settings are loaded from environment variables and validated using Pydantic.
    
    Used in:
    - main.py: For configuring the MCP server connection and Discord bot
    - client/mcp_client.py: For accessing server configuration
    - discord/bot.py: For Discord bot configuration
    
    Fields:
        server_script_path: Path to the MCP server script to connect to
        discord_enabled: Whether the Discord bot is enabled
        discord_command_prefix: The command prefix for Discord commands
    """
    server_script_path: str = "/Users/alejandro/repos/code/mcp/documentation/main.py"
    discord_enabled: bool = True
    discord_command_prefix: str = "!"


# Create a singleton instance of the settings
# This is imported by other modules to access configuration
settings = Settings()