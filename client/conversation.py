# ============================================================================
# CONVERSATION MANAGER
# ============================================================================
# This file implements a manager for handling conversations with users.
# It provides utilities for conversation history tracking and serialization.

import os
import json
from typing import List, Dict, Any
from datetime import datetime

# Import application logger
from utils.logger import logger


class ConversationManager:
    """Manager for handling and persisting user conversations"""
    
    def __init__(self, conversations_dir: str = "conversations"):
        """Initialize the conversation manager
        
        Args:
            conversations_dir: Directory for storing conversation logs
        """
        self.conversations_dir = conversations_dir
        self.logger = logger
        
        # Create the conversations directory if it doesn't exist
        os.makedirs(self.conversations_dir, exist_ok=True)
    
    def create_user_message(self, content: str) -> Dict[str, Any]:
        """Create a user message
        
        Args:
            content: The content of the message
            
        Returns:
            A formatted user message
        """
        return {"role": "user", "content": content}
    
    def create_system_message(self, content: str) -> Dict[str, Any]:
        """Create a system message
        
        Args:
            content: The content of the message
            
        Returns:
            A formatted system message
        """
        return {"role": "system", "content": content}
    
    def create_assistant_message(self, content: str, tool_calls: Any = None) -> Dict[str, Any]:
        """Create an assistant message
        
        Args:
            content: The content of the message
            tool_calls: Optional tool calls
            
        Returns:
            A formatted assistant message
        """
        message = {"role": "assistant", "content": content or ""}
        if tool_calls:
            message["tool_calls"] = tool_calls
        return message
    
    def create_tool_message(self, tool_call_id: str, content: str) -> Dict[str, Any]:
        """Create a tool response message
        
        Args:
            tool_call_id: The ID of the tool call
            content: The content of the message
            
        Returns:
            A formatted tool response message
        """
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content or ""
        }
    
    def get_default_system_message(self, persona: str = "crypto") -> Dict[str, Any]:
        """Get a default system message based on the specified persona
        
        Args:
            persona: The persona to use for the system message
            
        Returns:
            A formatted system message
        """
        personas = {
            "crypto": (
                "You are a helpful assistant with expertise in cryptocurrency research. "
                "You have access to web3-research-mcp tools that can help you gather information "
                "about various cryptocurrency tokens, market data, and blockchain projects."
            ),
            "general": "You are a helpful assistant.",
            "researcher": (
                "You are a research assistant with expertise in finding and analyzing information. "
                "You have access to search and research tools to help answer questions and gather data."
            )
        }
        
        content = personas.get(persona, personas["general"])
        return self.create_system_message(content)
    
    async def log_conversation(self, messages: List[Dict[str, Any]], prefix: str = "conversation") -> str:
        """Log a conversation to a file
        
        Args:
            messages: The conversation messages
            prefix: Prefix for the log file name
            
        Returns:
            The path to the log file
            
        Raises:
            Exception: If writing to the file fails
        """
        serializable_conversation = []

        # Process each message for serialization
        for message in messages:
            try:
                serializable_message = {"role": message["role"]}

                # Handle different content types (string vs list)
                if isinstance(message["content"], str):
                    serializable_message["content"] = message["content"]
                elif isinstance(message["content"], list):
                    serializable_message["content"] = []
                    # Process each content item based on its type
                    for content_item in message["content"]:
                        if hasattr(content_item, "to_dict"):
                            serializable_message["content"].append(
                                content_item.to_dict()
                            )
                        elif hasattr(content_item, "dict"):
                            serializable_message["content"].append(content_item.dict())
                        elif hasattr(content_item, "model_dump"):
                            serializable_message["content"].append(
                                content_item.model_dump()
                            )
                        else:
                            serializable_message["content"].append(content_item)
                
                # Handle tool_calls if present
                if "tool_calls" in message:
                    serializable_message["tool_calls"] = []
                    for tool_call in message["tool_calls"]:
                        if hasattr(tool_call, "to_dict"):
                            serializable_message["tool_calls"].append(tool_call.to_dict())
                        elif hasattr(tool_call, "dict"):
                            serializable_message["tool_calls"].append(tool_call.dict())
                        elif hasattr(tool_call, "model_dump"):
                            serializable_message["tool_calls"].append(tool_call.model_dump())
                        else:
                            # Try to convert to a serializable format
                            try:
                                serializable_message["tool_calls"].append(json.loads(json.dumps(tool_call, default=str)))
                            except:
                                self.logger.warning(f"Could not serialize tool_call: {tool_call}")
                                serializable_message["tool_calls"].append(str(tool_call))
                
                # Add tool_call_id if present (for tool responses)
                if "tool_call_id" in message:
                    serializable_message["tool_call_id"] = message["tool_call_id"]

                serializable_conversation.append(serializable_message)
            except Exception as e:
                self.logger.error(f"Error processing message: {str(e)}")
                self.logger.debug(f"Message content: {message}")
                raise

        # Generate timestamp for the log file
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath = os.path.join(self.conversations_dir, f"{prefix}_{timestamp}.json")

        try:
            with open(filepath, "w") as f:
                json.dump(serializable_conversation, f, indent=2, default=str)
            return filepath
        except Exception as e:
            self.logger.error(f"Error writing conversation to file: {str(e)}")
            raise
    
    def get_last_assistant_message(self, messages: List[Dict[str, Any]]) -> str:
        """Get the last assistant message from a conversation
        
        Args:
            messages: The conversation messages
            
        Returns:
            The content of the last assistant message, or an empty string if none
        """
        for message in reversed(messages):
            if message.get("role") == "assistant" and isinstance(message.get("content"), str):
                return message.get("content", "")
        return ""