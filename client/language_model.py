import os
import json
import re
from typing import List, Dict, Any, Optional

# Groq API client for LLM
from groq import Groq

# Import application logger
from utils.logger import logger


# Custom JSON encoder to handle Groq objects
class GroqEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Groq API objects"""
    def default(self, obj):
        # Handle tool calls and function objects from Groq
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        
        # For other types that can't be serialized
        try:
            return str(obj)
        except:
            return "[Object not serializable]"


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
                f"You have access to the following tools: {available_tools_str}. "
                "These tools can help you gather real-time information about cryptocurrency tokens, market data, and blockchain projects. "
                "When asked about cryptocurrency prices or market data, ALWAYS use the appropriate tools to fetch real-time information. "
                "For research queries about tokens, use research-related tools like research-token, research-source, or search. "
                "Return the research results even if price data is unavailable. "
                "Do not respond with disclaimers about not having real-time data when tools are available. "
                f"Only use the specific tool names listed above: {available_tools_str}. "
                "When calling tools, follow the exact format of tool_calls. Do not use text-based function calls or alternative formats. "
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
            
            # Check if query is about crypto prices
            is_price_query = False
            price_related_terms = ["price", "worth", "value", "cost", "bitcoin", "btc", "eth", "crypto"]
            
            # Check last user message for price-related content
            for message in reversed(messages_copy):
                if message.get("role") == "user":
                    user_query = message.get("content", "").lower()
                    if any(term in user_query for term in price_related_terms):
                        is_price_query = True
                        self.logger.info(f"Detected price-related query: {user_query}")
                    break
            
            # Get list of tool names if tools are provided
            tool_names = [tool["name"] for tool in (tools or [])]
            
            # Determine if we have any price-related tools
            has_price_tools = any("price" in tool.lower() or "crypto" in tool.lower() for tool in tool_names)
            
            # Add or update system message with appropriate tools guidance
            if not any(msg.get("role") == "system" for msg in messages_copy):
                # Add system message if not present
                system_message = self.create_system_message(tool_names)
                
                # If it's a price query and we have price tools, add helpful instruction
                if is_price_query and has_price_tools:
                    system_message["content"] += (
                        " For this cryptocurrency price query, consider using tools like get-price "
                        "or other available tools to fetch real-time data. This will provide more accurate "
                        "and up-to-date information than general responses."
                    )
                
                messages_copy.insert(0, system_message)
            else:
                # Update existing system message
                for i, msg in enumerate(messages_copy):
                    if msg.get("role") == "system":
                        updated_message = self.create_system_message(tool_names)
                        
                        # If it's a price query and we have price tools, add helpful instruction
                        if is_price_query and has_price_tools:
                            updated_message["content"] += (
                                " For this cryptocurrency price query, consider using tools like get-price "
                                "or other available tools to fetch real-time data. This will provide more accurate "
                                "and up-to-date information than general responses."
                            )
                        
                        messages_copy[i] = updated_message
                        break
            
            # Format tools for API call
            formatted_tools = None
            if tools:
                formatted_tools = []
                for tool in tools:
                    formatted_tool = {
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool.get("description", f"Tool for {tool['name']}"),
                        }
                    }
                    
                    # Add parameter schema if available
                    if "input_schema" in tool:
                        formatted_tool["function"]["parameters"] = tool["input_schema"]
                    
                    formatted_tools.append(formatted_tool)
            
            # Log the final messages for debugging - use custom encoder for Groq objects
            try:
                self.logger.info(f"Sending messages to LLM: {json.dumps(messages_copy, indent=2, cls=GroqEncoder)}")
            except Exception as e:
                self.logger.warning(f"Could not serialize messages for logging: {e}")
                self.logger.info(f"Sending {len(messages_copy)} messages to LLM")
            
            # Prepare parameters for the API call
            params = {
                "model": self.model_name,
                "max_tokens": max_tokens,
                "messages": messages_copy,
                "temperature": 0.7,
            }
            
            # Add tools parameter to the API call if available
            if formatted_tools:
                params["tools"] = formatted_tools
                
                # Always let the model decide which tool to use
                params["tool_choice"] = "auto"
                
                self.logger.info(f"Providing {len(formatted_tools)} tools to LLM")
            
            # Call the Groq API
            response = self.llm.chat.completions.create(**params)
            
            # Log a warning if we get an empty response but don't modify it
            if (not response.choices[0].message.content or 
                response.choices[0].message.content.strip() == ""):
                self.logger.warning("Received empty response from LLM. This may indicate an issue with the model or the prompt.")
            
            # Log the response for debugging - use custom encoder for safe logging
            content = response.choices[0].message.content or ""
            self.logger.info(f"LLM response: {content}")
            
            # Check if response contains tool calls
            if hasattr(response.choices[0].message, "tool_calls") and response.choices[0].message.tool_calls:
                try:
                    # Use custom encoder for safe logging - but avoid directly logging objects
                    tool_calls_info = []
                    for tool_call in response.choices[0].message.tool_calls:
                        try:
                            tool_info = {
                                "id": getattr(tool_call, "id", "unknown"),
                                "name": getattr(tool_call.function, "name", "unknown"),
                                "arguments": getattr(tool_call.function, "arguments", "{}")
                            }
                            tool_calls_info.append(tool_info)
                        except Exception:
                            tool_calls_info.append("Error extracting tool call info")
                    
                    self.logger.info(f"LLM response includes tool calls: {json.dumps(tool_calls_info)}")
                except Exception as e:
                    self.logger.info(f"LLM response includes tool calls but couldn't serialize for logging: {e}")
                
                # Add tool call indicators to the response content
                for tool_call in response.choices[0].message.tool_calls:
                    try:
                        function_name = tool_call.function.name
                        function_args = tool_call.function.arguments
                        content += f"\n<function={function_name}{function_args}>"
                    except Exception as e:
                        self.logger.warning(f"Error formatting tool call for content: {e}")
                
                # Update the response content
                response.choices[0].message.content = content
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error calling LLM: {e}")
            self.logger.exception("Exception details:")
            raise