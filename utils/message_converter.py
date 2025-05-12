"""Utility module for converting between different message formats."""

from typing import List, Dict, Any, Union
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, BaseMessage
import logging

logger = logging.getLogger(__name__)

def dict_to_langchain_messages(messages: List[Dict[str, Any]]) -> List[BaseMessage]:
    """Convert dictionary messages to LangChain message objects."""
    langchain_messages = []
    
    for message in messages:
        try:
            if message["role"] == "user":
                if isinstance(message["content"], str):
                    langchain_messages.append(HumanMessage(content=message["content"]))
                elif isinstance(message["content"], list):
                    # Handle tool results
                    for content_item in message["content"]:
                        if content_item.get("type") == "tool_result":
                            langchain_messages.append(ToolMessage(
                                content=content_item.get("content", ""),
                                tool_call_id=content_item.get("tool_use_id", "")
                            ))
            elif message["role"] == "assistant":
                if isinstance(message["content"], str):
                    langchain_messages.append(AIMessage(content=message["content"]))
                else:
                    # Convert content to string if it's not already
                    try:
                        content_str = str(message["content"]) if message["content"] else ""
                        langchain_messages.append(AIMessage(content=content_str))
                    except Exception as e:
                        logger.error(f"Error converting assistant message content: {e}")
                        langchain_messages.append(AIMessage(content=""))
            elif message["role"] == "system":
                langchain_messages.append(SystemMessage(content=message["content"]))
        except Exception as e:
            logger.error(f"Error converting message: {e}, message: {message}")
            # Add a default message to prevent errors
            if message.get("role") == "user":
                langchain_messages.append(HumanMessage(content=""))
            elif message.get("role") == "assistant":
                langchain_messages.append(AIMessage(content=""))
            elif message.get("role") == "system":
                langchain_messages.append(SystemMessage(content=""))
            
    return langchain_messages