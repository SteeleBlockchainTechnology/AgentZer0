# ============================================================================
# DISCORD EVENTS
# ============================================================================
# This file defines the event handlers for the Discord bot.
# It provides a structured way to organize and process Discord events.

import discord
from discord.ext import commands
import re
import json
import asyncio
from typing import Optional, List, Dict, Any

# Import application components
from client.mcp_client import MCPClient  # Client for MCP server communication
from utils.logger import logger          # Application logger


class EventHandler:
    """Event handler for Discord bot
    
    This class defines the event handlers for the Discord bot.
    It processes events like on_message, on_reaction_add, etc.
    """
    def __init__(self, bot, mcp_client: MCPClient):
        """Initialize the event handler
        
        Args:
            bot: The Discord bot instance
            mcp_client: The MCP client for processing queries
        """
        self.bot = bot
        self.mcp_client = mcp_client
        self.logger = logger
        
        # Store channels where the bot is actively conversing
        self.active_channels = set()
        
        # Track conversations in progress to avoid duplicate processing
        self.processing_queries = set()
        
        # Register event handlers
        self._register_events()
    
    def _register_events(self):
        """Register event handlers for Discord events
        
        Sets up the event handlers for various Discord events.
        """
        # Register on_message event
        @self.bot.event
        async def on_message(message):
            # Ignore messages from the bot itself or other bots
            if message.author == self.bot.user or message.author.bot:
                return
            
            # Process commands first (for !help, !tools, etc.)
            # This allows commands to use the shared self.mcp_client if they are designed to.
            await self.bot.process_commands(message)
            
            # If the message was handled by a command, don't process it further here.
            # This check assumes that commands consume the message context or that
            # bot.process_commands gives an indication. A common way is to check
            # if a command context was created and matched.
            # For simplicity, if it's a command, we assume it's handled.
            # You might need a more robust check depending on your command structure.
            if message.content.startswith(self.bot.command_prefix):
                return

            # Create a unique ID for this message to avoid processing duplicates
            message_id = f"{message.channel.id}_{message.id}"
            
            # Respond to all messages that aren't being processed yet
            if message_id not in self.processing_queries:
                # Add to processing set
                self.processing_queries.add(message_id)
                
                current_mcp_client_instance = None  # For cleanup in finally block
                try:
                    # Get the query text
                    query = message.content
                    
                    # Add this channel to active channels
                    self.active_channels.add(message.channel.id)
                    
                    # Send typing indicator to show bot is processing
                    async with message.channel.typing():
                        self.logger.info(f"Creating new MCPClient instance for query: {query}")
                        current_mcp_client_instance = MCPClient()

                        self.logger.info(f"Connecting new MCPClient instance for query: {query}")
                        # Initialize all servers and tools, not just connecting to a single server
                        if not await current_mcp_client_instance.initialize_servers():
                            self.logger.error(f"Failed to initialize MCPClient servers for query: {query}")
                            await message.reply("Sorry, I couldn't connect to my core services to process your request.")
                            return

                        self.logger.info(f"Processing Discord query with new MCPClient: {query}")
                        
                        # Process query using the new, isolated client instance
                        # This call will handle the full loop, including tool usage.
                        response_messages = await current_mcp_client_instance.process_query(query)
                        
                        # Get the last assistant message from the processed conversation
                        assistant_response = self._get_latest_assistant_message(response_messages)
                        
                        if assistant_response:
                            # Split long messages if needed (Discord has 2000 char limit)
                            if len(assistant_response) <= 2000:
                                await message.reply(assistant_response)
                            else:
                                # Split into chunks of 2000 chars
                                chunks = [assistant_response[i:i+2000] for i in range(0, len(assistant_response), 2000)]
                                for i, chunk in enumerate(chunks):
                                    if i == 0:
                                        await message.reply(chunk)
                                    else:
                                        await message.channel.send(chunk)
                        else:
                            # Fallback message if no response was found
                            await message.reply("I'm sorry, I'm having trouble processing that request. Could you try asking in a different way?")
                
                except Exception as e:
                    self.logger.error(f"Error processing Discord query with new MCPClient: {e}", exc_info=True)
                    await message.reply("Sorry, I encountered an error while processing your request.")
                finally:
                    # Ensure cleanup for the dynamically created client
                    if current_mcp_client_instance:
                        self.logger.info(f"Cleaning up MCPClient instance for query: {query}")
                        await current_mcp_client_instance.cleanup()
                    
                    # Remove from processing set
                    self.processing_queries.discard(message_id)
        
        # Register on_ready event
        @self.bot.event
        async def on_ready():
            self.logger.info(f"Discord bot logged in as {self.bot.user}")
            # Set bot status
            await self.bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.listening, 
                    name="all messages"
                )
            )
    
    def _get_latest_assistant_message(self, messages: List[Dict[str, Any]]) -> str:
        """Extract the latest assistant message from the conversation
        
        Args:
            messages: The conversation messages
            
        Returns:
            str: The content of the latest assistant message
        """
        # Loop through messages in reverse to find the last assistant message
        for msg in reversed(messages):
            if msg.get("role") == "assistant" and isinstance(msg.get("content"), str):
                return msg.get("content", "")
        return ""


def setup(bot, mcp_client: MCPClient):
    """Set up the event handlers
    
    This function creates and registers the event handlers with the bot.
    
    Args:
        bot: The Discord bot instance
        mcp_client: The MCP client for processing queries
    """
    return EventHandler(bot, mcp_client)