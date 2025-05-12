"""Event handlers for Discord bot integration with MCPClient."""
import asyncio
import logging
from discord import Message
from typing import Callable, Coroutine, Any

logger = logging.getLogger(__name__)

class MessageHandler:
    """Handles Discord messages and processes them through MCPClient."""
    
    def __init__(self, mcp_client):
        """Initialize the message handler.
        
        Args:
            mcp_client: The MCPClient instance to process messages.
        """
        self.mcp_client = mcp_client
        
    async def handle_message(self, message: Message) -> None:
        """Process a Discord message through the MCPClient.
        
        Args:
            message: The Discord message to process.
        """
        try:
            # Extract the message content
            query = message.content
            channel = message.channel
            
            # Let the user know we're processing their message
            async with channel.typing():
                # Process the query through MCPClient
                response_messages = await self.mcp_client.process_query(query)
                
                # Get the last assistant message
                for msg in reversed(response_messages):
                    if msg["role"] == "assistant" and isinstance(msg["content"], str):
                        # Send the response back to the Discord channel
                        await channel.send(msg["content"])
                        break
                    elif msg["role"] == "assistant" and isinstance(msg["content"], list):
                        # Handle complex responses (like those with tool calls)
                        for content_item in msg["content"]:
                            if isinstance(content_item, dict) and content_item.get("type") == "text":
                                await channel.send(content_item.get("text", ""))
                                break
        except Exception as e:
            logger.error(f"Error processing Discord message: {e}")
            await channel.send(f"Sorry, I encountered an error processing your request: {str(e)}")