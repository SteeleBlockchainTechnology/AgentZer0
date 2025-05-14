# ============================================================================
# DISCORD COMMANDS
# ============================================================================
# This file defines the command handlers for the Discord bot.
# It provides a structured way to organize and process Discord commands.

from discord.ext import commands
from typing import Optional, List, Dict, Any

# Import application components
from client.mcp_client import MCPClient  # Client for MCP server communication
from utils.logger import logger          # Application logger


class CommandCog(commands.Cog):
    """Command handler for Discord bot
    
    This class defines the command handlers for the Discord bot.
    It processes commands like !help, !tools, etc.
    
    Commands are registered using the @commands.command decorator.
    """
    def __init__(self, bot, mcp_client: MCPClient):
        """Initialize the command handler
        
        Args:
            bot: The Discord bot instance
            mcp_client: The MCP client for processing queries
        """
        self.bot = bot
        self.mcp_client = mcp_client
        self.logger = logger
    
    @commands.command(name="help")
    async def help_command(self, ctx):
        """Display help information about the bot"""
        help_text = (
            "**AgentZer0 Discord Bot**\n\n"
            "I can help answer your questions and perform tasks using AI.\n\n"
            "**How to use me:**\n"
            "- Mention me with your question: `@AgentZer0 what is the weather?`\n"
            "- Send me a direct message with your question\n\n"
            "**Available commands:**\n"
            "`!help` - Display this help message\n"
            "`!tools` - List available tools\n"
        )
        await ctx.send(help_text)
    
    @commands.command(name="tools")
    async def tools_command(self, ctx):
        """List available tools"""
        try:
            # Get tools from MCP client
            tools = await self.mcp_client.get_mcp_tools()
            
            # Format tools into a readable message
            tools_text = "**Available Tools:**\n\n"
            for tool in tools:
                tools_text += f"**{tool.name}**: {tool.description}\n\n"
            
            # Split long messages if needed
            if len(tools_text) <= 2000:
                await ctx.send(tools_text)
            else:
                # Split into chunks of 2000 chars
                chunks = [tools_text[i:i+2000] for i in range(0, len(tools_text), 2000)]
                for chunk in chunks:
                    await ctx.send(chunk)
        except Exception as e:
            self.logger.error(f"Error getting tools: {e}")
            await ctx.send("Sorry, I encountered an error while retrieving the tools.")


def setup(bot, mcp_client: MCPClient):
    """Set up the command handlers
    
    This function creates and registers the CommandCog with the bot.
    
    Args:
        bot: The Discord bot instance
        mcp_client: The MCP client for processing queries
    """
    bot.add_cog(CommandCog(bot, mcp_client))