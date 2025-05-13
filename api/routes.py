# ============================================================================
# API ROUTES
# ============================================================================
# This file defines the API endpoints for the AgentZer0 application.
# It connects the HTTP interface with the MCP client implementation.

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

# Import schema models for request/response validation
from models.schemas import QueryRequest, QueryResponse, ToolsResponse
# Import the MCP client for processing queries and accessing tools
from client.mcp_client import MCPClient

# Create FastAPI router for organizing endpoints
router = APIRouter()


# Dependency injection function to get the MCP client from app state
def get_mcp_client(request):
    """Get the MCP client from the FastAPI application state
    
    This dependency is used by route handlers to access the MCP client
    that was initialized in the application lifespan (main.py).
    
    Args:
        request: The FastAPI request object
        
    Returns:
        MCPClient: The initialized MCP client instance
    """
    return request.app.state.client


@router.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest, client: MCPClient = Depends(get_mcp_client)):
    """Process a user query and return the conversation response
    
    This endpoint:
    1. Receives a user query from the request body
    2. Passes the query to the MCP client for processing
    3. Returns the resulting conversation messages
    
    Route: POST /query
    
    Args:
        request: The validated query request containing the user's query
        client: The MCP client instance (injected via dependency)
        
    Returns:
        QueryResponse: The conversation messages resulting from the query
        
    Raises:
        HTTPException: If an error occurs during query processing
    """
    try:
        # Process the query using the MCP client and get conversation messages
        messages = await client.process_query(request.query)
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools", response_model=ToolsResponse)
async def get_tools(client: MCPClient = Depends(get_mcp_client)):
    """Get the list of available MCP tools
    
    This endpoint:
    1. Retrieves the list of available tools from the MCP client
    2. Formats the tools into the expected response format
    
    Route: GET /tools
    
    Args:
        client: The MCP client instance (injected via dependency)
        
    Returns:
        ToolsResponse: The list of available tools with their metadata
        
    Raises:
        HTTPException: If an error occurs while retrieving tools
    """
    try:
        # Get the list of tools from the MCP client
        tools = await client.get_mcp_tools()
        # Format the tools into the expected response format
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                }
                for tool in tools
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))