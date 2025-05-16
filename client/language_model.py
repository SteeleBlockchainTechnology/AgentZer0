import os
import json
import re
from typing import List, Dict, Any, Optional

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
        self.model_name = os.environ.get("GROQ_MODEL", "llama-3-8b-8192")
    
    def create_system_message(self, tool_names: List[str] = None) -> Dict[str, str]:
        """Create the system message with appropriate instructions
        
        Args:
            tool_names: List of available tool names to include in the system message
            
        Returns:
            Dict containing the system message
        """
        available_tools_str = ", ".join(f"`{name}`" for name in (tool_names or []))
        
        content = (
            "You are a helpful assistant with expertise in cryptocurrency research. "
        )
        
        if tool_names:
            content += (
                f"You have access to the following web3-research-mcp tools: {available_tools_str}. "
                "These tools can help you gather information about cryptocurrency tokens, market data, and blockchain projects. "
                "To use tools, format your response like this: <function=tool_name{\"param\":\"value\"}>. "
                "For example, to search for bitcoin price, use: <function=search{\"query\":\"bitcoin price\",\"searchType\":\"web\"}>. "
                "Always include explanatory text along with any function calls. "
                f"IMPORTANT: ONLY use the specific tool names listed above: {available_tools_str}. "
                "Do not invent or try to use tools that aren't in this list."
            )
        
        return {"role": "system", "content": content}
        
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
            
            # Make a copy to avoid modifying the original
            messages_copy = messages.copy()
            
            # Get list of tool names if tools are provided
            tool_names = [tool["name"] for tool in (tools or [])]
            
            # Add or update system message
            if not any(msg.get("role") == "system" for msg in messages_copy):
                # Add system message if not present
                system_message = self.create_system_message(tool_names)
                messages_copy.insert(0, system_message)
            
            # Check if last few messages were about tools and crypto prices/info
            # If so, encourage function calls more explicitly
            should_encourage_tools = False
            if len(messages_copy) >= 3 and tools:
                last_user_msg = None
                for msg in reversed(messages_copy):
                    if msg.get("role") == "user":
                        last_user_msg = msg.get("content", "").lower()
                        break
                
                if last_user_msg and any(term in last_user_msg for term in 
                                      ["price", "bitcoin", "btc", "eth", "crypto", "token", "coin"]):
                    should_encourage_tools = True
            
            if should_encourage_tools:
                # Add a reminder to use function calls if appropriate
                for i, msg in enumerate(messages_copy):
                    if msg.get("role") == "system":
                        messages_copy[i]["content"] += (
                            " For queries about cryptocurrency prices or market data, "
                            "please use the search tool or other available tools to get real-time information. "
                            "Always use <function=tool_name{...}> syntax when appropriate."
                        )
                        break
            
            # Log the final messages for debugging
            self.logger.info(f"Sending messages to LLM: {json.dumps(messages_copy, indent=2)}")
            
            # Prepare parameters for the API call
            params = {
                "model": self.model_name,
                "max_tokens": max_tokens,
                "messages": messages_copy,
                "temperature": 0.7,
            }
            
            # Explicitly do NOT add tools parameter to the API call
            # Instead, we'll rely on the function call format in the prompt
            
            # Call the Groq API
            response = self.llm.chat.completions.create(**params)
            
            # Log a warning if we get an empty response but don't modify it
            if (not response.choices[0].message.content or 
                response.choices[0].message.content.strip() == ""):
                self.logger.warning("Received empty response from LLM. This may indicate an issue with the model or the prompt.")
            
            # Check if response contains function call format
            content = response.choices[0].message.content or ""
            if "<function=" not in content and should_encourage_tools:
                # If expected to use tools but didn't, log a warning
                self.logger.warning("LLM response did not include function calls despite the topic being appropriate for tools.")
            
            # Log the response for debugging
            self.logger.info(f"LLM response: {response.choices[0].message.content}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error calling LLM: {e}")
            self.logger.exception("Exception details:")
            raise