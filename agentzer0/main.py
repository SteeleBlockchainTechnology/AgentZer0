"""
Main entry point for the AgentZer0 Discord bot.
"""
import os
import logging
import asyncio
from dotenv import load_dotenv

# Import components
from AgentZer0.discord_bot.bot import DiscordBot
from AgentZer0.discord_bot.events import DiscordEventHandler
from AgentZer0.llm.groq_client import GroqClient
from AgentZer0.mcp.client import MCPClient
from AgentZer0.mcp_servers.web3_research_server import Web3ResearchMCPServer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('agentzer0.log')
    ]
)

logger = logging.getLogger(__name__)

async def setup():
    """Set up the bot and all components."""
    logger.info("Starting AgentZer0 Discord bot setup...")
    
    # Initialize Discord bot
    discord_token = os.getenv("DISCORD_TOKEN")
    if not discord_token:
        logger.error("DISCORD_TOKEN not found in environment variables!")
        return
    
    prefix = os.getenv("DISCORD_PREFIX", "!")
    discord_bot = DiscordBot(discord_token, prefix)
    
    # Initialize GroqClient with dummy API key if not provided
    groq_api_key = os.getenv("GROQ_API_KEY", "dummy_api_key")
    groq_model = os.getenv("GROQ_MODEL", "llama-3-8b-8192")
    
    # Simple initialization without try/except since our client doesn't do any external calls
    groq_client = GroqClient(groq_api_key, groq_model)
    logger.info(f"Using simplified GroqClient")
    
    # Initialize MCP client
    mcp_client = MCPClient()
    
    # Initialize MCP servers
    web3_research_server = Web3ResearchMCPServer()
    
    # Register MCP servers
    mcp_client.register_server("web3_research", web3_research_server)
    
    # Set up Discord event handler with LLM processor
    async def process_message(message_content, conversation_history, context=None):
        return await groq_client.process_message(
            message_content, 
            conversation_history, 
            context,
            mcp_client
        )
    
    discord_event_handler = DiscordEventHandler(process_message)
    
    # Add message handler to Discord bot
    discord_bot.add_message_handler(discord_event_handler.handle_message)
    
    # Set up bot events
    await discord_bot.setup_events()
    
    logger.info("Bot setup complete. Starting bot...")
    return discord_bot

def main():
    """Main entry point."""
    try:
        # Using asyncio.run to handle the async setup
        discord_bot = asyncio.run(setup())
        
        if discord_bot:
            # Run the bot
            discord_bot.run()
        else:
            logger.error("Failed to set up bot. Exiting.")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)

if __name__ == "__main__":
    main()