# ============================================================================
# DISCORD EVENTS
# ============================================================================
# This file defines the event handlers for the Discord bot.
# It provides a structured way to organize and process Discord events.
# UPDATED to respond to all messages in channels, not just mentions/DMs

import discord
from discord.ext import commands
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
        
        # Register event handlers
        self._register_events()
    
    def _register_events(self):
        """Register event handlers for Discord events
        
        Sets up the event handlers for various Discord events.
        """
        # Register on_message event
        @self.bot.event
        async def on_message(message):
            # Ignore messages from the bot itself
            if message.author == self.bot.user:
                return
            
            # Process commands first (for !help, !tools, etc.)
            await self.bot.process_commands(message)
            
            # Check message type:
            is_dm = isinstance(message.channel, discord.DMChannel)
            is_mention = self.bot.user in message.mentions
            
            # Respond to:
            # 1. Direct messages
            # 2. Messages that mention the bot
            # 3. Messages in channels where bot is already active
            # 4. Messages that contain the bot's name (optional)
            
            should_respond = (
                is_dm or 
                is_mention or 
                message.channel.id in self.active_channels or
                self.bot.user.name.lower() in message.content.lower()  # Optional: comment this line if you don't want name triggers
            )
            
            if should_respond:
                # If the message mentions the bot, remove the mention from the message content
                query = message.content
                if is_mention:
                    query = query.replace(f"<@{self.bot.user.id}>", "").strip()
                
                # Add this channel to active channels
                self.active_channels.add(message.channel.id)
                
                # Send typing indicator to show bot is processing
                async with message.channel.typing():
                    try:
                        # Process the query through MCP client
                        self.logger.info(f"Processing Discord query: {query}")
                        messages = await self.mcp_client.process_query(query)
                        
                        # Get the assistant's response (last message)
                        for msg in messages:
                            if msg.get("role") == "assistant" and isinstance(msg.get("content"), str):
                                response = msg.get("content")
                                
                                # Split long messages if needed (Discord has 2000 char limit)
                                if len(response) <= 2000:
                                    await message.reply(response)
                                else:
                                    # Split into chunks of 2000 chars
                                    chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                                    for i, chunk in enumerate(chunks):
                                        # First chunk gets a reply, others are sent as messages
                                        if i == 0:
                                            await message.reply(chunk)
                                        else:
                                            await message.channel.send(chunk)
                    except Exception as e:
                        self.logger.error(f"Error processing Discord query: {e}")
                        await message.reply("Sorry, I encountered an error while processing your request.")
        
        # Register on_ready event
        @self.bot.event
        async def on_ready():
            self.logger.info(f"Discord bot logged in as {self.bot.user}")
            # Set bot status
            await self.bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.listening, 
                    name="your questions"
                )
            )


def setup(bot, mcp_client: MCPClient):
    """Set up the event handlers
    
    This function creates and registers the event handlers with the bot.
    
    Args:
        bot: The Discord bot instance
        mcp_client: The MCP client for processing queries
    """
    return EventHandler(bot, mcp_client)