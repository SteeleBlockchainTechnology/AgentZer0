"""
AgentZer0 Discord Bot - Entry Point
Integrates Discord functionality with Groq LLM and MCP client for cryptocurrency data.
"""
import asyncio
import os
import logging
import signal
import sys
from dotenv import load_dotenv

# Import our modular components
from client.mcp_client import MCPClientManager
from client.agent import GroqAgent
from discord_bot.bot import DiscordBot
from discord_bot.events import DiscordEvents

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('agentzer0.log')
    ]
)
logger = logging.getLogger(__name__)

class AgentZer0Bot:
    """Main application class that orchestrates all components."""
    
    def __init__(self):
        """Initialize the AgentZer0 bot."""
        self.mcp_client_manager = None
        self.agent = None
        self.discord_bot = None
        self.discord_events = None
        self.running = False
        
        # Load environment variables
        load_dotenv()
        self._validate_environment()
    
    def _validate_environment(self):
        """Validate required environment variables."""
        required_vars = ["GROQ_API_KEY", "DISCORD_BOT_TOKEN"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        logger.info("Environment variables validated successfully")
    
    async def initialize(self):
        """Initialize all components."""
        try:
            logger.info("Initializing AgentZer0 Discord Bot...")
            
            # Initialize MCP Client Manager
            config_path = "config/mcp_servers.json"
            self.mcp_client_manager = MCPClientManager(config_path)
            logger.info("MCP Client Manager initialized")
            
            # Initialize Groq Agent
            self.agent = GroqAgent(self.mcp_client_manager)
            await self.agent.setup_tools()
            logger.info("Groq Agent initialized with tools")
            
            # Initialize Discord Bot
            self.discord_bot = DiscordBot(self.agent)
            logger.info("Discord Bot initialized")
            
            # Initialize Discord Events
            self.discord_events = DiscordEvents(self.discord_bot, self.agent)
            logger.info("Discord Events initialized")
            
            logger.info("All components initialized successfully!")
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise
    
    async def start(self):
        """Start the bot."""
        if not self.discord_bot:
            await self.initialize()
        
        self.running = True
        logger.info("Starting AgentZer0 Discord Bot...")
        
        try:
            await self.discord_bot.start_bot()
        except Exception as e:
            logger.error(f"Bot startup failed: {e}")
            await self.shutdown()
            raise
    
    async def shutdown(self):
        """Gracefully shutdown the bot."""
        if not self.running:
            return
        
        logger.info("Shutting down AgentZer0 Discord Bot...")
        self.running = False
        
        try:
            # Cleanup MCP client first to ensure all connections are properly closed
            if self.mcp_client_manager:
                await self.mcp_client_manager.cleanup()
                logger.info("MCP client cleanup completed")
            
            # Close Discord connection
            if self.discord_bot:
                await self.discord_bot.close_bot()
                logger.info("Discord bot connection closed")
            
            logger.info("Shutdown completed successfully")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Global bot instance for signal handling
bot_instance = None

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    if bot_instance:
        asyncio.create_task(bot_instance.shutdown())

async def main():
    """Main entry point."""
    global bot_instance
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create and start bot
        bot_instance = AgentZer0Bot()
        await bot_instance.start()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        if bot_instance:
            await bot_instance.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)