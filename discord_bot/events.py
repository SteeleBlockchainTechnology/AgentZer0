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

            # Only process messages where the bot is mentioned
            if self.bot.user not in message.mentions:
                return
                
            # Create a unique ID for this message to avoid processing duplicates
            message_id = f"{message.channel.id}_{message.id}"
            
            # Respond to all messages that aren't being processed yet
            if message_id not in self.processing_queries:
                # Add to processing set
                self.processing_queries.add(message_id)
                
                current_mcp_client_instance = None  # For cleanup in finally block
                try:
                    # Get the query text - remove the mention of the bot
                    query = re.sub(f'<@!?{self.bot.user.id}>', '', message.content).strip()
                    
                    # If the query is empty after removing the mention, don't process it
                    if not query:
                        await message.reply("Hello! How can I help you today?")
                        return
                    
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
                            # Check if the response contains unprocessed function calls that need to be handled
                            function_patterns = [
                                r'<function=(\w+)\s*\{(.*?)\}>',
                                r'<function=(\w+)\s*\((.*?)\)>',
                                r'<function=(\w+)\s*\((.*?)\)</function>',
                                r'function=(\w+)\s*\((.*?)\)',
                                r'function=(\w+)\s*\{(.*?)\}',
                                r'<function=([\w-]+)\s*\((.*?)\)</function>',
                                r'<function=([\w-]+)\s+(.*?)></function>',
                                r'<function=([\w-]+)\s+(.*?)></function>',
                                r'<function=([\w-]+)\s+(.*?)</function>'
                            ]
                            
                            # Special case: If the entire response is just a function call
                            is_just_function_call = False
                            for pattern in function_patterns:
                                if re.match(f'^{pattern}$', assistant_response.strip()):
                                    is_just_function_call = True
                                    break
                            
                            if is_just_function_call:
                                self.logger.info("Response is only a single function call. Will process and use the result directly.")
                            
                            # Check if response contains any function calls (either the entire response or part of it)
                            contains_function_call = is_just_function_call  # Already true if it's just a function call
                            if not contains_function_call:
                                for pattern in function_patterns:
                                    if re.search(pattern, assistant_response):
                                        contains_function_call = True
                                        break
                            
                            if contains_function_call:
                                # Process the function call ourselves
                                self.logger.info("Response contains unprocessed function calls. Processing them now.")
                                self.logger.info(f"Original response: {assistant_response}")
                                
                                # Create a new query with just the function call to ensure it's processed properly
                                for pattern in function_patterns:
                                    matches = re.findall(pattern, assistant_response)
                                    
                                    if matches:
                                        self.logger.info(f"Found matches with pattern {pattern}: {matches}")
                                        for tool_name, tool_args_str in matches:
                                            try:
                                                # Process the function call
                                                self.logger.info(f"Executing function call: {tool_name} with args {tool_args_str}")
                                                
                                                # Fix common formatting issues in args
                                                if tool_args_str.startswith("{"): 
                                                    # Already valid JSON format
                                                    pass
                                                elif tool_args_str.startswith("\"") or tool_args_str.startswith("'"):
                                                    # String that might need wrapping
                                                    tool_args_str = "{\"query\": " + tool_args_str + "}"
                                                else:
                                                    # Wrap in curly braces if not already present
                                                    tool_args_str = '{' + tool_args_str + '}'
                                                
                                                # Clean up any potential issues
                                                tool_args_str = tool_args_str.replace("\\\"", "\"").replace("\\\'", "'")
                                                
                                                # Try to parse the arguments
                                                try:
                                                    tool_args = json.loads(tool_args_str)
                                                except json.JSONDecodeError as e:
                                                    # Try to fix common JSON syntax errors
                                                    fixed_str = re.sub(r'(\w+):', r'"\1":', tool_args_str)
                                                    tool_args = json.loads(fixed_str)
                                                
                                                # Find which server has this tool
                                                result = await current_mcp_client_instance.servers[current_mcp_client_instance._find_server_for_tool(tool_name)]["session"].call_tool(tool_name, tool_args)
                                                
                                                # Format the result
                                                tool_result = current_mcp_client_instance._format_tool_result(result.content)
                                                
                                                # If this is a research result, format it nicely
                                                if tool_name.startswith("research-") and isinstance(tool_result, str):
                                                    tool_result = self._format_research_result(tool_result)
                                                
                                                # Replace the function call with the actual result
                                                # Try different patterns of replacement based on the original function call format
                                                old_assistant_response = assistant_response  # Store original response to check if replacement worked
                                                
                                                # Try various replacement patterns
                                                patterns_to_try = [
                                                    f"<function={tool_name}\\({re.escape(tool_args_str)}\\)</function>",  # Full tag with parentheses
                                                    f"<function={tool_name}\\{{{re.escape(tool_args_str)}\\}}>",  # Open tag with braces
                                                    f"<function={tool_name}\\({re.escape(tool_args_str)}\\)>",  # Open tag with parentheses
                                                    f"<function={tool_name} {re.escape(tool_args_str)}</function>",  # With space separator
                                                    f"function={tool_name}\\({re.escape(tool_args_str)}\\)",  # No tags with parentheses
                                                    f"function={tool_name}\\{{{re.escape(tool_args_str)}\\}}"  # No tags with braces
                                                ]
                                                
                                                for pattern_to_try in patterns_to_try:
                                                    assistant_response = re.sub(pattern_to_try, tool_result, assistant_response)
                                                
                                                # If the response didn't change, the function call format might not have matched our patterns
                                                if assistant_response == old_assistant_response:
                                                    self.logger.warning(f"Failed to replace function call pattern for: {tool_name}. Using result directly.")
                                                    # If the response seems to be only the function call, just use the result directly
                                                    if re.match(r'^<function=.*>$', assistant_response.strip()) or re.match(r'^<function=.*</function>$', assistant_response.strip()) or is_just_function_call:
                                                        assistant_response = tool_result
                                                        self.logger.info(f"Using tool result directly: {tool_result[:100]}...")
                                                
                                            except Exception as e:
                                                self.logger.error(f"Error processing function call {tool_name}: {e}")
                                                # Replace function call with error message
                                                error_msg = f"Error executing {tool_name}: {str(e)}"
                                                
                                                # Try various replacement patterns
                                                old_assistant_response = assistant_response
                                                patterns_to_try = [
                                                    f"<function={tool_name}\\({re.escape(tool_args_str)}\\)</function>",  # Full tag with parentheses
                                                    f"<function={tool_name}\\{{{re.escape(tool_args_str)}\\}}>",  # Open tag with braces
                                                    f"<function={tool_name}\\({re.escape(tool_args_str)}\\)>",  # Open tag with parentheses
                                                    f"<function={tool_name} {re.escape(tool_args_str)}</function>",  # With space separator
                                                    f"function={tool_name}\\({re.escape(tool_args_str)}\\)",  # No tags with parentheses
                                                    f"function={tool_name}\\{{{re.escape(tool_args_str)}\\}}"  # No tags with braces
                                                ]
                                                
                                                for pattern_to_try in patterns_to_try:
                                                    assistant_response = re.sub(pattern_to_try, error_msg, assistant_response)
                                                
                                                # If the response didn't change, the function call format might not have matched our patterns
                                                if assistant_response == old_assistant_response:
                                                    self.logger.warning(f"Failed to replace function call pattern for error: {tool_name}. Using error message directly.")
                                                    # If the response seems to be only the function call, just use the error message directly
                                                    if re.match(r'^<function=.*>$', assistant_response.strip()) or re.match(r'^<function=.*</function>$', assistant_response.strip()) or is_just_function_call:
                                                        assistant_response = error_msg
                                                        self.logger.info(f"Using error message directly: {error_msg}")
                            
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
                    name="@mentions"
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
    
    def _format_research_result(self, content: str) -> str:
        """Format research results to be more readable
        
        Args:
            content: The research result content
            
        Returns:
            str: Formatted research result
        """
        if "search results" in content.lower():
            # Try to identify and format JSON search results
            try:
                parts = content.split("Search results:", 1)
                if len(parts) > 1:
                    header = parts[0].strip()
                    json_str = parts[1].strip()
                    
                    # Try to parse JSON
                    import json
                    results = json.loads(json_str)
                    
                    # Format results nicely
                    formatted = f"{header}\n\n**Search Results:**\n\n"
                    for i, result in enumerate(results):
                        formatted += f"{i+1}. **{result.get('title', 'Unknown')}**\n"
                        formatted += f"   {result.get('description', '')}\n"
                        formatted += f"   Source: {result.get('hostname', '')}\n"
                        formatted += f"   URL: {result.get('url', '')}\n\n"
                    
                    return formatted
            except Exception:
                # If parsing fails, return original content
                pass
        
        return content


def setup(bot, mcp_client: MCPClient):
    """Set up the event handlers
    
    This function creates and registers the event handlers with the bot.
    
    Args:
        bot: The Discord bot instance
        mcp_client: The MCP client for processing queries
    """
    return EventHandler(bot, mcp_client)