# ============================================================================
# API PACKAGE
# ============================================================================
# This package contains the API routes and endpoint handlers for the application.
#
# Key components:
# - routes.py: Defines the FastAPI routes that handle HTTP requests
#
# Connections:
# - Imported by main.py to include the API routes in the FastAPI application
# - Uses the client/mcp_client.py for processing queries and accessing tools
# - Uses models/schemas.py for request/response validation