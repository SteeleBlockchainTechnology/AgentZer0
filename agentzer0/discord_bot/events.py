"""
Discord event handlers and bot commands.
"""
import logging
import asyncio

logger = logging.getLogger(__name__)

class DiscordEventHandler:
    """Handles Discord events and forwards them to the LLM processor."""
    
    def __init__(self, llm_processor):
        """Initialize the Discord event handler.
        
        Args:
            llm_processor: LLM processor instance to handle messages.
        """
        self.llm_processor = llm_processor
        self.conversation_history = {}  # Store conversation history by channel ID
    
    async def handle_message(self, message):
        """Handle incoming Discord messages.
        
        Args:
            message (discord.Message): Message object from Discord.
        """
        # Get channel ID as conversation identifier
        channel_id = str(message.channel.id)
        
        # Initialize conversation history for this channel if it doesn't exist
        if channel_id not in self.conversation_history:
            self.conversation_history[channel_id] = []
        
        # Add user message to history
        self.conversation_history[channel_id].append({
            "role": "user",
            "name": message.author.name,
            "content": message.content
        })
        
        # Trim history if it gets too long (keep last 20 messages)
        if len(self.conversation_history[channel_id]) > 20:
            self.conversation_history[channel_id] = self.conversation_history[channel_id][-20:]
        
        # Typing indicator to show the bot is "thinking"
        async with message.channel.typing():
            try:
                # Send "thinking" message if processing might take a while
                thinking_msg = await message.channel.send("Thinking...")
                
                # Process the message with LLM
                response = await self.llm_processor(
                    message.content,
                    self.conversation_history[channel_id],
                    context={
                        "channel_id": channel_id,
                        "user_id": str(message.author.id),
                        "guild_id": str(message.guild.id) if message.guild else None,
                        "username": message.author.name
                    }
                )
                
                # Delete the "thinking" message
                await thinking_msg.delete()
                
                # Add assistant response to history
                self.conversation_history[channel_id].append({
                    "role": "assistant",
                    "content": response
                })
                
                # Send response (handle Discord's 2000 character limit)
                if len(response) <= 2000:
                    await message.channel.send(response)
                else:
                    # Split long messages
                    for i in range(0, len(response), 2000):
                        chunk = response[i:i+2000]
                        await message.channel.send(chunk)
                        # Small delay to keep messages in order
                        await asyncio.sleep(0.5)
                        
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                await message.channel.send(f"Sorry, I encountered an error: {str(e)}")