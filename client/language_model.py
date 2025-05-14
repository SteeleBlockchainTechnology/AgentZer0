# ============================================================================
# LANGUAGE MODEL CLIENT
# ============================================================================
# This file implements the client for interacting with the Groq LLM.
# It's separated from the MCP client to improve modularity and separation of concerns.

import os
import json
from typing import List, Dict, Any, Optional
import asyncio

# Groq API client for LLM
from groq import Groq

# Import application logger
from utils.logger import logger


class LanguageModelClient:
    """Client for interacting with the Groq Language Model"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the language model client
        
        Args:
            api_key: Optional API key for the Groq API. If not provided,
                    it will be read from the GROQ_API_KEY environment variable.
        """
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
            
        self.llm = Groq(api_key=self.api_key)
        self.logger = logger
        self.model_name = "llama-3.3-70b-versatile"
        
    async def generate_completion(self, 
                                 messages: List[Dict[str, Any]], 
                                 tools: Optional[List[Dict[str, Any]]] = None,
                                 max_tokens: int = 1000) -> Any:
        """Generate a completion from the language model
        
        Args:
            messages: The conversation history in the ChatML format
            tools: Optional list of tools to make available to the model
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            The completion response from the Groq API
            
        Raises:
            Exception: If the API call fails
        """
        try:
            self.logger.info(f"Calling LLM with {len(messages)} messages")
            
            # Add a system message if not already present
            if not any(msg.get("role") == "system" for msg in messages):
                messages.insert(0, {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant with expertise in cryptocurrency research. "
                        "You have access to web3-research-mcp tools that can help you gather information "
                        "about various cryptocurrency tokens, market data, and blockchain projects."
                    )
                })
            
            # Prepare parameters for the API call
            params = {
                "model": self.model_name,
                "max_tokens": max_tokens,
                "messages": messages,
            }
            
            # Add tools if provided
            if tools:
                # Make sure tools are properly formatted for the API
                validated_tools = self._validate_tools(tools)
                if validated_tools:
                    self.logger.info(f"Using {len(validated_tools)} tools")
                    params["tools"] = validated_tools
                    params["tool_choice"] = "auto"
                    
                    # Log the first tool for debugging
                    if validated_tools:
                        self.logger.info(f"First tool format: {json.dumps(validated_tools[0], indent=2)}")
            
            # Call the Groq API
            response = self.llm.chat.completions.create(**params)
            return response
            
        except Exception as e:
            self.logger.error(f"Error calling LLM: {e}")
            raise
            
    def _validate_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and format tools for the Groq API
        
        Ensures that tools have the correct format required by the API.
        
        Args:
            tools: List of tools to validate
            
        Returns:
            List of validated and formatted tools
        """
        validated_tools = []
        
        # Handle empty tools list
        if not tools:
            # Create a dummy search tool if no tools are available
            dummy_tool = {
                "type": "function",
                "function": {
                    "name": "search",
                    "description": "Search for information on the web",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
            return [dummy_tool]
        
        # Process each tool
        for tool in tools:
            # Check if the tool already has the correct format
            if "type" in tool and tool["type"] == "function" and "function" in tool:
                # Tool is already in the correct format
                validated_tool = tool
            else:
                # Tool needs to be converted to the correct format
                name = tool.get("name", "unknown_tool")
                
                # Ensure description is not null
                description = tool.get("description")
                if not description:
                    description = f"Tool for {name.replace('-', ' ')}"
                
                # Ensure parameters are valid
                parameters = tool.get("inputSchema") or tool.get("parameters") or {"type": "object", "properties": {}}
                
                # Create properly formatted tool
                validated_tool = {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "parameters": parameters
                    }
                }
            
            # Add the validated tool to the list
            validated_tools.append(validated_tool)
            
        return validated_tools