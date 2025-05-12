"""Utility module for converting between different tool formats."""

from typing import List, Dict, Any
from langchain_core.tools import Tool

def dict_to_langchain_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert dictionary tools to the format expected by LangChain Chat Models.
    
    Args:
        tools: List of dictionary tools with 'name', 'description', and 'input_schema' keys
        
    Returns:
        List of tool specifications in LangChain format
    """
    langchain_tools = []
    
    for tool in tools:
        # Ensure description is a valid string, default to empty string if missing or None
        description = tool.get("description") or ""
        
        # Convert to the format expected by LangChain Chat Models
        langchain_tools.append({
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": description,
                "parameters": tool.get("input_schema", {})
            }
        })
            
    return langchain_tools