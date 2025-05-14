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
                system_message = {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant with expertise in cryptocurrency research. "
                        "You have access to web3-research-mcp tools that can help you gather information "
                        "about various cryptocurrency tokens, market data, and blockchain projects. "
                        "To use tools, format your response like this: <function=tool_name{\"param\":\"value\"}>. "
                        "For example, to search for bitcoin price, use: <function=search{\"query\":\"bitcoin price\",\"searchType\":\"web\"}>. "
                        "Always include explanatory text along with any function calls."
                    )
                }
                messages.insert(0, system_message)
            else:
                # Ensure system message emphasizes the function call format
                for i, msg in enumerate(messages):
                    if msg.get("role") == "system" and "<function=" not in msg.get("content", ""):
                        messages[i]["content"] = (
                            "You are a helpful assistant with expertise in cryptocurrency research. "
                            "You have access to web3-research-mcp tools that can help you gather information "
                            "about various cryptocurrency tokens, market data, and blockchain projects. "
                            "To use tools, format your response like this: <function=tool_name{\"param\":\"value\"}>. "
                            "For example, to search for bitcoin price, use: <function=search{\"query\":\"bitcoin price\",\"searchType\":\"web\"}>. "
                            "Always include explanatory text along with any function calls."
                        )
                        break
            
            # Check if last few messages were about tools and crypto prices/info
            # If so, encourage function calls more explicitly
            should_encourage_tools = False
            if len(messages) >= 3:
                last_user_msg = None
                for msg in reversed(messages):
                    if msg.get("role") == "user":
                        last_user_msg = msg.get("content", "").lower()
                        break
                
                if last_user_msg and any(term in last_user_msg for term in 
                                      ["price", "bitcoin", "btc", "eth", "crypto", "token", "coin"]):
                    should_encourage_tools = True
            
            if should_encourage_tools:
                # Add a reminder to use function calls if appropriate
                for i, msg in enumerate(messages):
                    if msg.get("role") == "system":
                        messages[i]["content"] += (
                            " For queries about cryptocurrency prices or market data, "
                            "please use the search tool or other available tools to get real-time information. "
                            "Always use <function=tool_name{...}> syntax when appropriate."
                        )
                        break
            
            # Log the final messages for debugging
            self.logger.info(f"Sending messages to LLM: {json.dumps(messages, indent=2)}")
            
            # Prepare parameters for the API call
            params = {
                "model": self.model_name,
                "max_tokens": max_tokens,
                "messages": messages,
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