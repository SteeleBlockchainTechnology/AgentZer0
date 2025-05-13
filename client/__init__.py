# ============================================================================
# CLIENT PACKAGE
# ============================================================================
# This package contains the client implementation for communicating with the MCP server.
#
# Key components:
# - mcp_client.py: Implements the MCPClient class for MCP server communication and LLM interaction
#
# Connections:
# - Used by main.py for initializing the client during application startup
# - Used by api/routes.py for processing queries and accessing tools
# - Uses utils/logger.py for logging operations and errors
# - Uses config/settings.py for server configuration