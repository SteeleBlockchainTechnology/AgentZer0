# ============================================================================
# MCP CLIENT UPDATED FOR WEB3 RESEARCH MCP
# ============================================================================
# This file implements the client for communicating with web3-research-mcp server.

import asyncio
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

# Import application logger
from utils.logger import logger

# Import settings
from config.settings import settings


class MCPClient:
    """Client for interacting with the MCP server and Groq LLM"""
    def __init__(self):
        """Initialize the MCP client"""
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.llm = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.tools = []
        self.messages = []
        self.logger = logger

    async def connect_to_server(self, _=None):
        """Connect to the web3-research-mcp server
        
        Note: The parameter is ignored and settings are used instead
        
        Returns:
            bool: True if connection was successful
        """
        try:
            # Set up the npx command to run the web3-research-mcp package
            server_params = StdioServerParameters(
                command=settings.mcp_command,
                args=settings.mcp_args,
                env=None  # Use the current environment
            )

            # Log the command being executed
            self.logger.info(f"Starting MCP server with: {settings.mcp_command} {' '.join(settings.mcp_args)}")

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

            self.logger.info("Connected to web3-research-mcp server")

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

            # Log available tool names
            tool_names = [tool["name"] for tool in self.tools]
            self.logger.info(f"Available tools: {tool_names}")

            return True

        except Exception as e:
            self.logger.error(f"Error connecting to MCP server: {e}")
            traceback.print_exc()
            raise

    async def get_mcp_tools(self):
        """Get the list of available tools from the MCP server"""
        try:
            response = await self.session.list_tools()
            return response.tools
        except Exception as e:
            self.logger.error(f"Error getting MCP tools: {e}")
            raise

    async def process_query(self, query: str):
        """Process a user query through the LLM and MCP tools"""
        try:
            self.logger.info(f"Processing query: {query}")
            # Initialize conversation with user query
            user_message = {"role": "user", "content": query}
            self.messages = [user_message]

            # Continue conversation until a final response is reached
            while True:
                # Get response from LLM
                response = await self.call_llm()

                # Extract the message from the response
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
                            self.logger.info(f"Tool {tool_name} result received")
                            
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

            return self.messages

        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            raise

    async def call_llm(self):
        """Call the Groq LLM with the current conversation"""
        try:
            self.logger.info("Calling LLM")
            # Add a system message if not already present
            if not any(msg.get("role") == "system" for msg in self.messages):
                self.messages.insert(0, {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant with expertise in cryptocurrency research. "
                        "You have access to web3-research-mcp tools that can help you gather information "
                        "about various cryptocurrency tokens, market data, and blockchain projects."
                    )
                })
                
            # Call the Groq API
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
        """Clean up resources when shutting down"""
        try:
            await self.exit_stack.aclose()
            self.logger.info("Disconnected from MCP server")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            traceback.print_exc()
            raise

    async def log_conversation(self):
        """Log the current conversation to a file"""
        # Create conversations directory if it doesn't exist
        os.makedirs("conversations", exist_ok=True)

        serializable_conversation = []

        # Process each message for serialization
        for message in self.messages:
            try:
                serializable_message = {"role": message["role"]}

                # Handle different content types (string vs list)
                if isinstance(message["content"], str):
                    serializable_message["content"] = message["content"]
                elif isinstance(message["content"], list):
                    serializable_message["content"] = []
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
            raise