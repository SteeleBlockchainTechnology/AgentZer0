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
            await self.bot.process_commands(message)
            
            # Create a unique ID for this message to avoid processing duplicates
            message_id = f"{message.channel.id}_{message.id}"
            
            # Respond to all messages that aren't being processed yet
            if message_id not in self.processing_queries:
                # Add to processing set
                self.processing_queries.add(message_id)
                
                try:
                    # Get the query text
                    query = message.content
                    
                    # Add this channel to active channels
                    self.active_channels.add(message.channel.id)
                    
                    # Send typing indicator to show bot is processing
                    async with message.channel.typing():
                        # Process the query through MCP client
                        self.logger.info(f"Processing Discord query: {query}")
                        
                        # Process query and get response
                        messages = await self.mcp_client.process_query(query)
                        
                        # Get the last assistant message
                        assistant_response = self._get_latest_assistant_message(messages)
                        
                        # Check if function call is in progress
                        if "<function=" in assistant_response:
                            # If function call is in progress, tell the user we're working on it
                            interim_message = await message.reply("I'm using my tools to find information for you. Please wait a moment...")
                            
                            # Wait for a moment to allow tools to complete
                            await asyncio.sleep(1)
                            
                            # Process the query again to get the final result after tool usage
                            messages = await self.mcp_client.process_query(query)
                            
                            # Get the updated response
                            assistant_response = self._get_latest_assistant_message(messages)
                            
                            # Edit the interim message with the final response
                            await interim_message.edit(content=assistant_response)
                        else:
                            # Send the response directly
                            if assistant_response:
                                # Split long messages if needed (Discord has 2000 char limit)
                                if len(assistant_response) <= 2000:
                                    await message.reply(assistant_response)
                                else:
                                    # Split into chunks of 2000 chars
                                    chunks = [assistant_response[i:i+2000] for i in range(0, len(assistant_response), 2000)]
                                    for i, chunk in enumerate(chunks):
                                        # First chunk gets a reply, others are sent as messages
                                        if i == 0:
                                            await message.reply(chunk)
                                        else:
                                            await message.channel.send(chunk)
                            else:
                                # Fallback message if no response was found
                                await message.reply("I'm sorry, I'm having trouble processing that request. Could you try asking in a different way?")
                except Exception as e:
                    self.logger.error(f"Error processing Discord query: {e}")
                    await message.reply("Sorry, I encountered an error while processing your request.")
                finally:
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