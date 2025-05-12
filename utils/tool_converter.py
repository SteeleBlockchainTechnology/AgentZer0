"""Utility module for converting between different tool formats.

This module provides functions to convert between dictionary-based tool formats
and LangChain tool objects.
"""

from typing import List, Dict, Any
from langchain_core.tools import Tool


def dict_to_langchain_tools(tools: List[Dict[str, Any]]) -> List[Tool]:
    """Convert dictionary tools to LangChain tool objects.
    
    Args:
        tools: List of dictionary tools with 'name', 'description', and 'input_schema' keys
        
    Returns:
        List of LangChain tool objects
    """
    langchain_tools = []
    
    for tool in tools:
        # Ensure description is a valid string, default to empty string if missing or None
        description = tool.get("description") or ""
        
        langchain_tools.append(
            Tool(
                name=tool.get("name", ""),  # Also handle missing name
                description=description,
                func=lambda x: x,  # Placeholder function, actual calls handled separately
                args_schema=tool.get("input_schema")
            )
        )
            
    return langchain_tools