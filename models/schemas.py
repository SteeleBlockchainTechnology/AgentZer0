from pydantic import BaseModel
from typing import Dict, Any, List, Optional

# ============================================================================
# SCHEMA MODELS
# ============================================================================
# This file defines all the data models used throughout the application.
# These models are used for request/response validation and serialization in the API.
# They connect the API routes with the client implementation.

class QueryRequest(BaseModel):
    """Request model for query processing
    
    Used in: /api/routes.py - process_query endpoint
    This model validates the incoming query request from users.
    
    Fields:
        query: The text query from the user to be processed by the LLM
    """
    query: str


class Message(BaseModel):
    """Message model for conversation
    
    Used in: client/mcp_client.py - process_query method
    Represents a message in the conversation between user and assistant.
    
    Fields:
        role: The sender of the message ("user" or "assistant")
        content: The content of the message (can be text or structured data)
    """
    role: str
    content: Any


class ToolCall(BaseModel):
    """Tool call model
    
    Used in: client/mcp_client.py when processing tool calls
    Represents a call to an external tool by the LLM.
    
    Fields:
        name: The name of the tool to call
        args: The arguments to pass to the tool
    """
    name: str
    args: Dict[str, Any]


class ToolResponse(BaseModel):
    """Response model for tool listing
    
    Used in: /api/routes.py - get_tools endpoint
    Represents a single tool available in the MCP system.
    
    Fields:
        name: The name of the tool
        description: A description of what the tool does
        input_schema: The JSON schema defining the tool's input parameters
    """
    name: str
    description: str
    input_schema: Dict[str, Any]


class ToolsResponse(BaseModel):
    """Response model for tools endpoint
    
    Used in: /api/routes.py - get_tools endpoint
    Container for the list of available tools.
    
    Fields:
        tools: List of available tools with their metadata
    """
    tools: List[ToolResponse]


class QueryResponse(BaseModel):
    """Response model for query endpoint
    
    Used in: /api/routes.py - process_query endpoint
    Contains the conversation messages resulting from processing a query.
    
    Fields:
        messages: The conversation history including user queries and assistant responses
    """
    messages: List[Dict[str, Any]]