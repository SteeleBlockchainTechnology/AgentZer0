# ============================================================================
# DISCORD PACKAGE
# ============================================================================
# This package contains the Discord bot implementation for AgentZer0.
#
# Key components:
# - bot.py: Implements the DiscordBot class for Discord server communication
# - commands.py: Defines the Discord command handlers
# - events.py: Handles Discord events like messages and reactions
#
# Connections:
# - Used by main.py for initializing the Discord bot during application startup
# - Uses client/mcp_client.py for processing queries through the MCP
# - Uses utils/logger.py for logging operations and errors
# - Uses config/settings.py for Discord configuration