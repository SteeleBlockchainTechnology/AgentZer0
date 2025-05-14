# ============================================================================
# DISCORD EVENTS
# ============================================================================
# This file defines the event handlers for the Discord bot.
# It provides a structured way to organize and process Discord events.
# UPDATED with direct fix for response handling

import discord
from discord.ext import commands
import re
import json
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
                        
                        # Find the most recent assistant message
                        assistant_response = self._get_latest_assistant_message(messages)
                        
                        # Prepare a readable response
                        readable_response = self._prepare_readable_response(assistant_response)
                        
                        # Send the response
                        if readable_response:
                            # Split long messages if needed (Discord has 2000 char limit)
                            if len(readable_response) <= 2000:
                                await message.reply(readable_response)
                            else:
                                # Split into chunks of 2000 chars
                                chunks = [readable_response[i:i+2000] for i in range(0, len(readable_response), 2000)]
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
    
    def _prepare_readable_response(self, content: str) -> str:
        """Convert an assistant message to a readable response
        
        This handles special formats like function calls and ensures a readable response.
        
        Args:
            content: The raw content from the assistant message
            
        Returns:
            str: A human-readable response
        """
        if not content:
            return "I'm sorry, I don't have a response for that query."

        # Check if content is a JSON string of messages (common error pattern)
        if content.strip().startswith("[") and content.strip().endswith("]"):
            try:
                # Try to parse as JSON
                json_content = json.loads(content)
                
                # If it's a list of messages, extract the assistant message
                if isinstance(json_content, list):
                    for msg in reversed(json_content):
                        if msg.get("role") == "assistant" and isinstance(msg.get("content"), str):
                            content = msg.get("content", "")
                            break
            except:
                # If parsing fails, keep original content
                pass
        
        # Replace function call syntax with readable text
        function_pattern = r'<function=(\w+)(?:\{(.*?)\})?(?:>.*?</function>|>)'
        
        def replace_function(match):
            func_name = match.group(1)
            params_json = match.group(2) if match.group(2) else "{}"
            
            try:
                params = json.loads(params_json)
                if func_name == "search":
                    query = params.get("query", "information")
                    return f"I'm searching for information about '{query}'. Please wait a moment..."
                else:
                    return f"I'm using my {func_name.replace('-', ' ')} tool to gather information for you. Please wait a moment..."
            except:
                return f"I'm using my {func_name.replace('-', ' ')} tool to gather information for you. Please wait a moment..."
        
        processed_content = re.sub(function_pattern, replace_function, content)
        
        # Return the processed content
        return processed_content


def setup(bot, mcp_client: MCPClient):
    """Set up the event handlers
    
    This function creates and registers the event handlers with the bot.
    
    Args:
        bot: The Discord bot instance
        mcp_client: The MCP client for processing queries
    """
    return EventHandler(bot, mcp_client)