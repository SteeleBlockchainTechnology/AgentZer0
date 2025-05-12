"""
Simplified Groq LLM integration for the AgentZer0 Discord bot.
"""
import json
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class GroqClient:
    """Client for interacting with Groq LLM API."""
    
    def __init__(self, api_key, model="llama-3-8b-8192"):
        """Initialize the Groq client.
        
        Args:
            api_key (str): Groq API key.
            model (str): Groq model to use.
        """
        self.api_key = api_key
        self.model = model
        
        # Simple initialization - we'll import and create the client only when needed
        logger.info(f"GroqClient initialized with model: {model}")
        
        # Use a thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        # System message template
        self.system_message = """
        You are a helpful assistant in a Discord server, equipped with tools that you can use to assist users.
        When asked a question or given a task, think about which tools would be most helpful for solving it.
        If you need to use a tool, follow this process:
        1. Think about which tool is appropriate
        2. Call the tool with the necessary parameters
        3. Use the result to inform your response
        
        Always be helpful, concise, and friendly in your responses.
        """
    
    async def process_message(self, user_message, conversation_history, context=None, mcp_client=None):
        """Process a user message and generate a response.
        
        Args:
            user_message (str): Message from the user.
            conversation_history (list): List of previous messages.
            context (dict, optional): Additional context about the message.
            mcp_client (MCPClient, optional): MCP client for tool execution.
            
        Returns:
            str: Response from the LLM.
        """
        # Prepare messages for the API
        messages = [
            {"role": "system", "content": self.system_message}
        ]
        
        # Add conversation history
        for msg in conversation_history:
            messages.append(msg)
        
        # Import Groq client only when needed
        from groq import Groq
        import httpx
        
        # Create Groq client instance with minimal parameters
        # Avoid using any additional parameters that might cause conflicts
        try:
            # First try with just the API key
            client = Groq(api_key=self.api_key)
        except TypeError as e:
            # If that fails, try a more direct approach without additional imports
            logger.warning(f"Error initializing Groq client: {e}")
            
            # Create a basic client with only the essential parameters
            # The base_url is the standard Groq API endpoint
            client = Groq(
                api_key=self.api_key,
                base_url="https://api.groq.com/openai/v1"
            )
        
        # Add user message to conversation
        messages.append({"role": "user", "content": user_message})
        
        # Call Groq API with proper error handling
        try:
            chat_completion = client.chat.completions.create(
                messages=messages,
                model=self.model,
            )
            
            # Get the response content
            response = chat_completion.choices[0].message.content
            return response
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}")
            return f"I'm sorry, I encountered an error while processing your request: {str(e)}"
        
    
    # We can add more realistic LLM functionality later when the basic structure works