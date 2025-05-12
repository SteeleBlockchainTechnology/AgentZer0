"""Utility module for converting between different message formats.

This module provides functions to convert between dictionary-based message formats
and LangChain message objects.
"""

from typing import List, Dict, Any, Union
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, BaseMessage


def dict_to_langchain_messages(messages: List[Dict[str, Any]]) -> List[BaseMessage]:
    """Convert dictionary messages to LangChain message objects.
    
    Args:
        messages: List of dictionary messages with 'role' and 'content' keys
        
    Returns:
        List of LangChain message objects
    """
    langchain_messages = []
    
    for message in messages:
        if message["role"] == "user":
            if isinstance(message["content"], str):
                langchain_messages.append(HumanMessage(content=message["content"]))
            else:
                # Handle tool results
                for content_item in message["content"]:
                    if content_item.get("type") == "tool_result":
                        langchain_messages.append(ToolMessage(
                            content=content_item["content"],
                            tool_call_id=content_item["tool_use_id"]
                        ))
        elif message["role"] == "assistant":
            if isinstance(message["content"], str):
                langchain_messages.append(AIMessage(content=message["content"]))
            else:
                # For tool calls, the content structure is handled in the response processing
                langchain_messages.append(AIMessage(content=message["content"]))
        elif message["role"] == "system":
            langchain_messages.append(SystemMessage(content=message["content"]))
            
    return langchain_messages


def langchain_to_dict_messages(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
    """Convert LangChain message objects to dictionary messages.
    
    Args:
        messages: List of LangChain message objects
        
    Returns:
        List of dictionary messages with 'role' and 'content' keys
    """
    dict_messages = []
    
    for message in messages:
        if isinstance(message, HumanMessage):
            dict_messages.append({"role": "user", "content": message.content})
        elif isinstance(message, AIMessage):
            dict_messages.append({"role": "assistant", "content": message.content})
        elif isinstance(message, SystemMessage):
            dict_messages.append({"role": "system", "content": message.content})
        elif isinstance(message, ToolMessage):
            dict_messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": message.tool_call_id,
                    "content": message.content
                }]
            })
            
    return dict_messages