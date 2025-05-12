"""
Tests for the Discord bot module.
"""
import pytest
import discord.ext.commands
from unittest.mock import AsyncMock, MagicMock, patch

from discord_mcp_bot.discord_bot.bot import DiscordBot
from discord_mcp_bot.discord_bot.events import DiscordEventHandler

@pytest.fixture
def discord_bot():
    """Fixture for creating a Discord bot instance."""
    with patch('discord.ext.commands.Bot'):
        bot = DiscordBot("test_token", "!")
        return bot

@pytest.fixture
def event_handler():
    """Fixture for creating a Discord event handler."""
    processor_mock = AsyncMock()
    handler = DiscordEventHandler(processor_mock)
    return handler, processor_mock

"""
Tests for the Discord bot module.
"""
import pytest
import discord.ext.commands
from unittest.mock import AsyncMock, MagicMock, patch

from discord_mcp_bot.discord_bot.bot import DiscordBot
from discord_mcp_bot.discord_bot.events import DiscordEventHandler

@pytest.fixture
def discord_bot():
    """Fixture for creating a Discord bot instance."""
    with patch('discord.ext.commands.Bot'):
        bot = DiscordBot("test_token", "!")
        return bot

@pytest.fixture
def event_handler():
    """Fixture for creating a Discord event handler."""
    processor_mock = AsyncMock()
    handler = DiscordEventHandler(processor_mock)
    return handler, processor_mock

class TestDiscordBot:
    """Tests for the DiscordBot class."""
    
    def test_init(self, discord_bot):
        """Test initialization of the Discord bot."""
        assert discord_bot.token == "test_token"
        assert discord_bot.prefix == "!"
        assert discord_bot.message_handlers == []
    
    def test_add_message_handler(self, discord_bot):
        """Test adding a message handler."""
        handler = AsyncMock()
        discord_bot.add_message_handler(handler)
        assert handler in discord_bot.message_handlers

    @pytest.mark.asyncio
    async def test_setup_events(self, discord_bot):
        """Test setting up events."""
        await discord_bot.setup_events()
        # This just tests that the method runs without error
        # More detailed tests would mock the bot events
        assert True

class TestDiscordEventHandler:
    """Tests for the DiscordEventHandler class."""
    
    def test_init(self, event_handler):
        """Test initialization of the event handler."""
        handler, processor = event_handler
        assert handler.llm_processor == processor
        assert handler.conversation_history == {}
    
    @pytest.mark.asyncio
    async def test_handle_message(self, event_handler):
        """Test handling a message."""
        handler, processor = event_handler
        
        # Mock message
        message = MagicMock()
        message.channel.id = "12345"
        message.author.name = "TestUser"
        message.content = "Hello, bot!"
        message.author.id = "67890"
        message.guild.id = "09876"
        
        # Mock channel typing context
        message.channel.typing.return_value.__aenter__ = AsyncMock()
        message.channel.typing.return_value.__aexit__ = AsyncMock()
        
        # Mock thinking message
        thinking_msg = AsyncMock()
        message.channel.send = AsyncMock(return_value=thinking_msg)
        
        # Set processor return value
        processor.return_value = "Hello, human!"
        
        # Call the method
        await handler.handle_message(message)
        
        # Verify conversation history was updated
        channel_id = str(message.channel.id)
        assert channel_id in handler.conversation_history
        assert len(handler.conversation_history[channel_id]) == 2
        assert handler.conversation_history[channel_id][0]["role"] == "user"
        assert handler.conversation_history[channel_id][0]["content"] == "Hello, bot!"
        assert handler.conversation_history[channel_id][1]["role"] == "assistant"
        assert handler.conversation_history[channel_id][1]["content"] == "Hello, human!"
        
        # Verify processor was called
        processor.assert_called_once_with(
            "Hello, bot!",
            handler.conversation_history[channel_id][0:1],  # Only the user message
            context={
                "channel_id": channel_id,
                "user_id": "67890",
                "guild_id": "09876",
                "username": "TestUser"
            }
        )
        
        # Verify messages were sent
        assert message.channel.send.call_count == 2
        thinking_msg.delete.assert_called_once()
        
        # The second call to send should have the response
        message.channel.send.assert_called_with("Hello, human!")