# ============================================================================
# DISCORD BOT
# ============================================================================
# This file implements the Discord bot for AgentZer0.
# It connects the Discord interface with the MCP client for processing queries.
# It uses the commands.py and events.py modules for handling commands and events.

import os
import asyncio
from typing import Optional, List, Dict, Any

# Discord.py library for Discord API integration
import discord  # This imports the discord.py package
from discord.ext import commands  # This imports from the discord.py package

# Import Discord modules (these are local to your project)
from . import commands as cmd_module
from . import events as event_module

# Import application components
from client.mcp_client import MCPClient  # Client for MCP server communication
from utils.logger import logger          # Application logger


class DiscordBot:
    """Discord bot for AgentZer0
    
    This class handles:
    1. Connection to Discord using the Discord API token
    2. Processing messages from Discord users
    3. Routing queries to the MCP client for processing
    4. Sending responses back to Discord users
    5. Managing Discord-specific events and commands
    
    The bot acts as a bridge between Discord users and the MCP client.
    """
    def __init__(self, mcp_client: MCPClient):
        """Initialize the Discord bot
        
        Sets up the bot with intents and command prefix.
        Stores a reference to the MCP client for processing queries.
        
        Args:
            mcp_client: The initialized MCP client instance
        """
        # Set up Discord intents (permissions)
        intents = discord.Intents.default()
        intents.message_content = True  # Enable message content intent
        
        # Create Discord bot instance with command prefix
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        
        # Store reference to MCP client
        self.mcp_client = mcp_client
        
        # Set up logger
        self.logger = logger
        
        # Set up command and event handlers
        self.setup_handlers()
        
        # Track active conversations
        self.active_conversations = {}
    
    def setup_handlers(self):
        """Set up command and event handlers
        
        Initializes the command and event handlers for the Discord bot.
        """
        # Set up command handlers
        cmd_module.setup(self.bot, self.mcp_client)
        
        # Set up event handlers
        self.event_handler = event_module.setup(self.bot, self.mcp_client)
    
    async def start(self, token: str):
        """Start the Discord bot
        
        Connects to Discord using the provided token and starts listening for events.
        
        Args:
            token: The Discord bot token for authentication
            
        Raises:
            Exception: If connection to Discord fails
        """
        try:
            self.logger.info("Starting Discord bot")
            await self.bot.start(token)
        except Exception as e:
            self.logger.error(f"Error starting Discord bot: {e}")
            raise
    
    async def close(self):
        """Close the Discord bot connection
        
        Disconnects from Discord and performs cleanup.
        Called during application shutdown.
        
        Raises:
            Exception: If disconnection fails
        """
        try:
            self.logger.info("Closing Discord bot connection")
            await self.bot.close()
        except Exception as e:
            self.logger.error(f"Error closing Discord bot: {e}")
            raise