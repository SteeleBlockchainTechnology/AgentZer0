import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', force=True)
logger = logging.getLogger(__name__)

# Ensure logs are displayed
logging.getLogger().handlers[0].setLevel(logging.INFO)

# Import the GroqClient
from AgentZer0.llm.groq_client import GroqClient

def main():
    # Get API key from environment
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        logger.error("GROQ_API_KEY not found in environment variables!")
        return
    
    # Initialize Groq client
    try:
        groq_client = GroqClient(groq_api_key)
        logger.info(f"Successfully initialized Groq client with model: {groq_client.model}")
        # Test accessing a property to verify it works
        _ = groq_client.client.chat
        logger.info("Successfully accessed client.chat property")
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {e}", exc_info=True)
        return
    
    logger.info("Groq client test completed successfully")

if __name__ == "__main__":
    main()