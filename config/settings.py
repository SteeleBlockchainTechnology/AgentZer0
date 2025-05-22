# ============================================================================
# APPLICATION SETTINGS FOR WEB3 RESEARCH MCP
# ============================================================================
# Updated settings for working with the web3-research-mcp package

from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

# Load environment variables from .env file if present
load_dotenv()


class MCPServerConfig:
    """Configuration for a single MCP server
    
    This class defines the configuration for a single MCP server connection.
    """
    def __init__(self, name: str, command: str = "npx", args: list = ["-y", "coincap-mcp"]):
        self.name = name        # Unique identifier for this server
        self.command = command  # Command to run the server
        self.args = args        # Arguments for the command


class Settings(BaseSettings):
    """Application settings loaded from environment variables
    
    This class defines the configuration settings for the application,
    supporting multiple MCP server connections.
    """
    # MCP Server Configuration
    # List of MCP server configurations
    mcp_servers: list = []
    
    # Default MCP command and args for backward compatibility
    default_mcp_command: str = "npx"
    default_mcp_args: list = ["-y", "coincap-mcp"]
    
    # Discord Bot Configuration
    discord_enabled: bool = True
    discord_command_prefix: str = "!"


# Create a singleton instance of the settings
settings = Settings()

# Add the default MCP server directly to the list


# Add the coincap-mcp server

settings.mcp_servers.append(MCPServerConfig(
    name="crypto",
    command="python",
    args=[os.path.join(os.path.dirname(__file__), "..", "mcp_servers", "crypto-market-data", "server.py")]
))
settings.mcp_servers.append(MCPServerConfig(
    name="web3-research-mcp",
    command="npx",
    args=["-y", "web3-research-mcp@latest"]
))
# Example of how to add additional MCP servers
# Uncomment and modify these lines to add your own servers

'''
Example usage:

# Add another MCP server with different configuration
settings.mcp_servers.append(MCPServerConfig(
    name="custom_server",
    command="python",
    args=["path/to/custom_mcp_server.py"]
))

# Add a third MCP server running a JavaScript implementation
settings.mcp_servers.append(MCPServerConfig(
    name="js_server",
    command="node",
    args=["path/to/js_server.js"]
))
'''