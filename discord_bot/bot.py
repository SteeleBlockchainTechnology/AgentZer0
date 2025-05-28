import os
import logging

import discord

from discord.ext import commands
print("discord.py imported successfully")
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class DiscordBot:
    """Discord bot wrapper with enhanced configuration."""
    
    def __init__(self, agent_processor=None):
        """Initialize Discord bot.
        
        Args:
            agent_processor: Agent processor instance for handling queries
        """
        self.agent_processor = agent_processor
        self.bot_token = os.getenv("DISCORD_BOT_TOKEN")
        self.bot_user_id = None
        
        if not self.bot_token:
            raise ValueError("DISCORD_BOT_TOKEN not found in environment variables")
        
        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True  # Required to read message content
        intents.members = True  # For member-related features
        
        # Initialize bot
        self.bot = commands.Bot(
            command_prefix='!',  # Fallback prefix, mainly using @mentions
            intents=intents,
            help_command=None  # Disable default help command
        )
        
        # Rate limiting storage
        self.user_cooldowns = {}
        self.rate_limit_seconds = int(os.getenv("RATE_LIMIT_SECONDS", "5"))
        
        logger.info("Discord bot initialized")
    
    def get_bot(self):
        """Get the Discord bot instance."""
        return self.bot
    
    async def start_bot(self):
        """Start the Discord bot."""
        try:
            await self.bot.start(self.bot_token)
        except Exception as e:
            logger.error(f"Failed to start Discord bot: {e}")
            raise
    
    async def close_bot(self):
        """Close the Discord bot connection."""
        await self.bot.close()
        logger.info("Discord bot connection closed")
    
    def set_agent_processor(self, agent_processor):
        """Set the agent processor for handling queries."""
        self.agent_processor = agent_processor
    
    def is_rate_limited(self, user_id: int) -> bool:
        """Check if user is rate limited."""
        import time
        current_time = time.time()
        last_request = self.user_cooldowns.get(user_id, 0)
        
        if current_time - last_request < self.rate_limit_seconds:
            return True
        
        self.user_cooldowns[user_id] = current_time
        return False
    
    def extract_mention_content(self, message: discord.Message) -> Optional[str]:
        """Extract content from message after removing bot mention.
        
        Args:
            message: Discord message object
            
        Returns:
            Cleaned message content or None if not a valid mention
        """
        if not self.bot_user_id:
            return None
        
        # Check if bot is mentioned
        if self.bot.user not in message.mentions:
            return None
        
        # Remove bot mention from content
        content = message.content
        mention_patterns = [
            f'<@{self.bot_user_id}>',
            f'<@!{self.bot_user_id}>',
        ]
        
        for pattern in mention_patterns:
            content = content.replace(pattern, '').strip()
        
        return content if content else None
    
    def get_message_context(self, message: discord.Message, history_limit: int = 5) -> str:
        """Get context from recent messages in the channel.
        
        Args:
            message: Current message
            history_limit: Number of previous messages to include
            
        Returns:
            String containing message history context
        """
        # This will be implemented in events.py where we have access to the message history
        return ""
