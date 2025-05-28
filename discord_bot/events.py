import discord
from discord.ext import commands
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

class DiscordEvents:
    """Handles Discord events and message processing."""
    
    def __init__(self, bot_instance, agent_processor=None):
        """Initialize Discord events handler.
        
        Args:
            bot_instance: DiscordBot instance
            agent_processor: Agent processor for handling queries
        """
        self.bot_instance = bot_instance
        self.agent_processor = agent_processor
        self.bot = bot_instance.get_bot()
        
        # Register event handlers
        self._register_events()
        
        logger.info("Discord events handler initialized")
    
    def _register_events(self):
        """Register Discord event handlers."""
        
        @self.bot.event
        async def on_ready():
            """Called when bot is ready."""
            logger.info(f'{self.bot.user} has connected to Discord!')
            logger.info(f'Bot ID: {self.bot.user.id}')
            
            # Store bot user ID for mention detection
            self.bot_instance.bot_user_id = self.bot.user.id
            
            # Set bot status
            await self.bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="for @mentions | Crypto data at your service!"
                )
            )
        
        @self.bot.event
        async def on_message(message):
            """Handle incoming messages."""
            # Ignore messages from the bot itself
            if message.author == self.bot.user:
                return
            
            # Check if bot is mentioned
            if self.bot.user not in message.mentions:
                return
            
            # Check rate limiting
            if self.bot_instance.is_rate_limited(message.author.id):
                await message.reply("⏰ Please wait a moment before sending another request.", 
                                  mention_author=False)
                return
            
            # Extract query content
            query = self.bot_instance.extract_mention_content(message)
            if not query:
                await message.reply("👋 Hello! Please include your question after mentioning me.", 
                                  mention_author=False)
                return
            
            # Show typing indicator
            async with message.channel.typing():
                try:
                    # Get message context
                    context = await self._get_message_context(message)
                    
                    # Process query with agent
                    result = await self._process_query_with_agent(query, context, message)
                    
                    # Send response
                    await self._send_response(message, result)
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await message.reply(f"❌ Sorry, I encountered an error: {str(e)}", 
                                      mention_author=False)
        
        @self.bot.event
        async def on_error(event, *args, **kwargs):
            """Handle Discord errors."""
            logger.error(f"Discord error in {event}: {args}")
        
        @self.bot.event
        async def on_command_error(ctx, error):
            """Handle command errors."""
            logger.error(f"Command error: {error}")
    
    async def _get_message_context(self, message: discord.Message, history_limit: int = 5) -> str:
        """Get context from recent messages in the channel.
        
        Args:
            message: Current message
            history_limit: Number of previous messages to include
            
        Returns:
            String containing message history context
        """
        try:
            # Get recent messages from the channel
            messages = []
            async for msg in message.channel.history(limit=history_limit + 1, before=message):
                # Skip bot messages and very old messages
                if msg.author != self.bot.user:
                    messages.append(f"{msg.author.display_name}: {msg.content[:100]}")
            
            if messages:
                return "Recent conversation: " + " | ".join(reversed(messages[-3:]))
            return ""
        except Exception as e:
            logger.debug(f"Could not get message context: {e}")
            return ""
    
    async def _process_query_with_agent(self, query: str, context: str, message: discord.Message) -> dict:
        """Process query using the agent processor.
        
        Args:
            query: User's query
            context: Message context
            message: Original Discord message
            
        Returns:
            Dictionary with processing results
        """
        if not self.agent_processor:
            return {
                'success': False,
                'response': "🔧 Agent processor not available. Please check the configuration.",
                'error': "No agent processor"
            }
        
        try:
            # Add Discord-specific context
            discord_context = f"Discord user: {message.author.display_name}"
            if message.guild:
                discord_context += f" | Server: {message.guild.name}"
            if context:
                discord_context += f" | {context}"
            
            result = await self.agent_processor.process_query(query, discord_context)
            return result
            
        except Exception as e:
            logger.error(f"Error in agent processing: {e}")
            return {
                'success': False,
                'response': f"🔧 Processing error: {str(e)}",
                'error': str(e)
            }
    
    async def _send_response(self, message: discord.Message, result: dict):
        """Send response back to Discord.
        
        Args:
            message: Original Discord message
            result: Processing result from agent
        """
        response = result.get('response', 'No response generated')
        
        # Add status emoji based on success
        if result.get('success', False):
            if len(response) > 1900:  # Discord message limit with some buffer
                # Split long responses
                chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await message.reply(f"📊 {chunk}", mention_author=False)
                    else:
                        await message.channel.send(f"📊 (continued) {chunk}")
            else:
                await message.reply(f"📊 {response}", mention_author=False)
        else:
            await message.reply(f"❌ {response}", mention_author=False)
        
        # Log the interaction
        logger.info(f"Processed query from {message.author.display_name}: '{result.get('query', 'Unknown')}' - Success: {result.get('success', False)}")
    
    def set_agent_processor(self, agent_processor):
        """Set the agent processor for handling queries."""
        self.agent_processor = agent_processor
        logger.info("Agent processor set for Discord events")
