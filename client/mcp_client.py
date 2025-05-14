# Fixed version of mcp_client.py for Groq v0.4.2
# This replaces the import of ChatCompletion and updates any related code

# ============================================================================
# MCP CLIENT
# ============================================================================
# This file implements the client for communicating with the MCP server and LLM.
# It serves as the core component that connects the API with the MCP ecosystem.

from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack
import traceback
import os
import json
from datetime import datetime

# MCP client libraries for server communication
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Groq API client for LLM
from groq import Groq
# Remove or comment out the ChatCompletion import as it's not available in this version
# from groq.types import ChatCompletion  

# Import application logger
from utils.logger import logger


class MCPClient:
    """Client for interacting with the MCP server and Groq LLM
    
    This class handles:
    1. Connection to the MCP server via stdio transport
    2. Retrieval of available tools from the MCP server
    3. Processing user queries through the LLM
    4. Executing tool calls based on LLM responses
    5. Maintaining conversation state
    6. Logging conversations for debugging and analysis
    
    The client acts as a bridge between the FastAPI routes and the underlying
    MCP and LLM functionality.
    """
    def __init__(self):
        """Initialize the MCP client
        
        Sets up the client with empty session, tools, and messages.
        Initializes the Groq client for LLM communication.
        """
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None  # MCP client session
        self.exit_stack = AsyncExitStack()            # For managing async context
        self.llm = Groq(api_key=os.environ.get("GROQ_API_KEY"))  # Groq API client
        self.tools = []                               # Available MCP tools
        self.messages = []                            # Conversation history
        self.logger = logger                          # Application logger

    async def connect_to_server(self, server_script_path: str):
        """Connect to the MCP server
        
        Establishes a connection to the MCP server using the provided script path.
        Initializes the session and retrieves available tools.
        
        Args:
            server_script_path: Path to the MCP server script (.py or .js)
            
        Returns:
            bool: True if connection was successful
            
        Raises:
            ValueError: If the server script is not a .py or .js file
            Exception: If connection fails for any other reason
        """
        try:
            # Determine the script type and appropriate command
            is_python = server_script_path.endswith(".py")
            is_js = server_script_path.endswith(".js")
            if not (is_python or is_js):
                raise ValueError("Server script must be a .py or .js file")

            # Set up the command to run the server script
            command = "python" if is_python else "node"
            server_params = StdioServerParameters(
                command=command, args=[server_script_path], env=None
            )

            # Establish stdio transport connection
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.stdio, self.write = stdio_transport
            
            # Create and initialize the MCP client session
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )

            await self.session.initialize()

            self.logger.info("Connected to MCP server")

            # Retrieve and format available tools from the server
            mcp_tools = await self.get_mcp_tools()
            self.tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                }
                for tool in mcp_tools
            ]

            self.logger.info(
                f"Available tools: {[tool['name'] for tool in self.tools]}"
            )

            return True

        except Exception as e:
            self.logger.error(f"Error connecting to MCP server: {e}")
            traceback.print_exc()
            raise

    async def get_mcp_tools(self):
        """Get the list of available tools from the MCP server
        
        Retrieves the tools that can be used by the LLM from the MCP server.
        
        Returns:
            List: The available tools with their metadata
            
        Raises:
            Exception: If tool retrieval fails
        """
        try:
            response = await self.session.list_tools()
            return response.tools
        except Exception as e:
            self.logger.error(f"Error getting MCP tools: {e}")
            raise

    async def process_query(self, query: str):
        """Process a user query through the LLM and MCP tools
        
        This method:
        1. Initializes a new conversation with the user query
        2. Calls the LLM to generate a response
        3. Handles tool calls if the LLM requests them
        4. Continues the conversation until a final text response is generated
        5. Logs the conversation for debugging
        
        Args:
            query: The user's text query
            
        Returns:
            List[Dict]: The conversation messages
            
        Raises:
            Exception: If query processing fails
        """
        try:
            self.logger.info(f"Processing query: {query}")
            # Initialize conversation with user query
            user_message = {"role": "user", "content": query}
            self.messages = [user_message]

            # Continue conversation until a final response is reached
            while True:
                # Get response from LLM
                response = await self.call_llm()

                # Extract the message from the response using the correct structure for Groq v0.4.2
                # The response structure in v0.4.2 might be different from what was initially expected
                # Assuming the response follows a standard structure similar to OpenAI's
                message = response.choices[0].message
                
                # Check if the message has tool calls
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    # Process tool calls
                    assistant_message = {
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": message.tool_calls
                    }
                    self.messages.append(assistant_message)
                    await self.log_conversation()
                    
                    # Process each tool call
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        tool_use_id = tool_call.id
                        self.logger.info(
                            f"Calling tool {tool_name} with args {tool_args}"
                        )
                        try:
                            # Execute the tool call via MCP
                            result = await self.session.call_tool(tool_name, tool_args)
                            self.logger.info(f"Tool {tool_name} result: {result}...")
                            
                            # Add tool result to conversation
                            self.messages.append(
                                {
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "tool_result",
                                            "tool_use_id": tool_use_id,
                                            "content": result.content,
                                        }
                                    ],
                                }
                            )
                            await self.log_conversation()
                        except Exception as e:
                            self.logger.error(f"Error calling tool {tool_name}: {e}")
                            raise
                else:
                    # Simple text response
                    assistant_message = {
                        "role": "assistant",
                        "content": message.content,
                    }
                    self.messages.append(assistant_message)
                    await self.log_conversation()
                    break

                # Tool calls are now processed in the code above

            return self.messages

        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            raise

    async def call_llm(self):
        """Call the Groq LLM with the current conversation
        
        Sends the current conversation history to the LLM and gets a response.
        The LLM may generate a text response or request to use tools.
        
        Returns:
            The LLM response (structure depends on Groq API version)
            
        Raises:
            Exception: If the LLM call fails
        """
        try:
            self.logger.info("Calling LLM")
            # Add a system message if not already present
            if not any(msg.get("role") == "system" for msg in self.messages):
                self.messages.insert(0, {
                    "role": "system",
                    "content": "You are a helpful assistant with access to tools."
                })
                
            return self.llm.chat.completions.create(
                model="llama-3.3-70b-versatile",  # Groq model version
                max_tokens=1000,                 # Maximum response length
                messages=self.messages,          # Conversation history
                tools=self.tools,                # Available tools
            )
        except Exception as e:
            self.logger.error(f"Error calling LLM: {e}")
            raise

    async def cleanup(self):
        """Clean up resources when shutting down
        
        Closes the connection to the MCP server and releases resources.
        Called during application shutdown in the lifespan context manager.
        
        Raises:
            Exception: If cleanup fails
        """
        try:
            await self.exit_stack.aclose()
            self.logger.info("Disconnected from MCP server")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            traceback.print_exc()
            raise

    async def log_conversation(self):
        """Log the current conversation to a file
        
        Saves the conversation history to a JSON file in the 'conversations' directory.
        Handles serialization of different message content types.
        
        Raises:
            Exception: If logging fails
        """
        # Create conversations directory if it doesn't exist
        os.makedirs("conversations", exist_ok=True)

        serializable_conversation = []

        # Process each message for serialization
        for message in self.messages:
            try:
                serializable_message = {"role": message["role"], "content": []}

                # Handle different content types (string vs list)
                if isinstance(message["content"], str):
                    serializable_message["content"] = message["content"]
                elif isinstance(message["content"], list):
                    # Process each content item based on its type
                    for content_item in message["content"]:
                        if hasattr(content_item, "to_dict"):
                            serializable_message["content"].append(
                                content_item.to_dict()
                            )
                        elif hasattr(content_item, "dict"):
                            serializable_message["content"].append(content_item.dict())
                        elif hasattr(content_item, "model_dump"):
                            serializable_message["content"].append(
                                content_item.model_dump()
                            )
                        else:
                            serializable_message["content"].append(content_item)
                
                # Handle tool_calls if present
                if "tool_calls" in message:
                    serializable_message["tool_calls"] = []
                    for tool_call in message["tool_calls"]:
                        if hasattr(tool_call, "to_dict"):
                            serializable_message["tool_calls"].append(tool_call.to_dict())
                        elif hasattr(tool_call, "dict"):
                            serializable_message["tool_calls"].append(tool_call.dict())
                        elif hasattr(tool_call, "model_dump"):
                            serializable_message["tool_calls"].append(tool_call.model_dump())
                        else:
                            # Try to convert to a serializable format
                            try:
                                serializable_message["tool_calls"].append(json.loads(json.dumps(tool_call, default=str)))
                            except:
                                self.logger.warning(f"Could not serialize tool_call: {tool_call}")
                                serializable_message["tool_calls"].append(str(tool_call))

                serializable_conversation.append(serializable_message)
            except Exception as e:
                self.logger.error(f"Error processing message: {str(e)}")
                self.logger.debug(f"Message content: {message}")
                raise

        # Generate timestamp for the log file
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath = os.path.join("conversations", f"conversation_{timestamp}.json")

        try:
            with open(filepath, "w") as f:
                json.dump(serializable_conversation, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Error writing conversation to file: {str(e)}")
            self.logger.debug(f"Serializable conversation: {serializable_conversation}")
            raise