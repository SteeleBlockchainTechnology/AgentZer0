from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack
import traceback
import json
import os
from datetime import datetime

# Import application components
from utils.logger import logger
from client.language_model import LanguageModelClient
from config.settings import settings

# MCP client libraries
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    """Client for the MCP server.
    
    Manages connection to the MCP server, fetches tools, and processes queries using Groq LLM.
    """
    
    def __init__(self):
        """Initialize the MCP client."""
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.tools: List[Dict[str, Any]] = []
        self.messages: List[Dict[str, Any]] = []
        self.logger = logger
        
        # Initialize Groq language model client
        self.api_key = os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            self.logger.warning("GROQ_API_KEY environment variable is not set")
        self.llm = LanguageModelClient(api_key=self.api_key)

    async def connect_to_server(self, server_script_path: str) -> bool:
        """Connect to the MCP server.
        
        Args:
            server_script_path: Path to the MCP server script (.py or .js)
            
        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            # Validate server script extension
            is_python = server_script_path.endswith(".py")
            is_js = server_script_path.endswith(".js")
            if not (is_python or is_js):
                raise ValueError("Server script must be a .py or .js file")

            # Set up command based on script type
            command = "python" if is_python else "node"
            server_params = StdioServerParameters(
                command=command, args=[server_script_path], env=None
            )

            self.logger.info(f"Starting MCP server with: {command} {server_script_path}")

            # Establish connection
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.stdio, self.client = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.client)
            )

            await self.session.initialize()
            self.logger.info("Connected to MCP server")

            # Fetch and format tools
            mcp_tools = await self.get_mcp_tools()
            self.tools = [
                {
                    "name": tool.name,
                    "description": tool.description or f"Tool for {tool.name.replace('-', ' ')}",
                    "inputSchema": tool.inputSchema,
                }
                for tool in mcp_tools
            ]
            self.logger.info(f"Available tools: {[tool['name'] for tool in self.tools]}")

            return True

        except Exception as e:
            self.logger.error(f"Error connecting to MCP server: {e}")
            traceback.print_exc()
            return False

    async def get_mcp_tools(self):
        """Get the list of available tools from the MCP server.
        
        Returns:
            List of available tools
        """
        try:
            response = await self.session.list_tools()
            return response.tools
        except Exception as e:
            self.logger.error(f"Error getting MCP tools: {e}")
            raise

    async def process_query(self, query: str) -> List[Dict[str, Any]]:
        """Process a user query.
        
        Sends query to Groq LLM, processes tool calls, and returns conversation messages.
        
        Args:
            query: The user's query text
            
        Returns:
            List[Dict[str, Any]]: The conversation messages
        """
        try:
            self.logger.info(f"Processing query: {query}")
            # Initialize conversation with system and user messages
            system_message = {
                "role": "system",
                "content": (
                    "You are a helpful assistant with expertise in cryptocurrency research. "
                    "You have access to web3-research-mcp tools to gather information about "
                    "cryptocurrency tokens, market data, and blockchain projects."
                ),
            }
            user_message = {"role": "user", "content": query}
            self.messages = [system_message, user_message]

            while True:
                response = await self.call_llm()

                # Handle text response (no tool calls)
                if not hasattr(response.choices[0].message, "tool_calls") or not response.choices[0].message.tool_calls:
                    assistant_message = {
                        "role": "assistant",
                        "content": response.choices[0].message.content or "",
                    }
                    self.messages.append(assistant_message)
                    await self.log_conversation()
                    break

                # Handle tool calls
                message = response.choices[0].message
                assistant_message = {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "name": tool_call.function.name,
                            "arguments": json.loads(tool_call.function.arguments),
                        }
                        for tool_call in message.tool_calls
                    ],
                }
                self.messages.append(assistant_message)
                await self.log_conversation()

                # Process each tool call
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    tool_use_id = tool_call.id
                    self.logger.info(f"Calling tool {tool_name} with args {tool_args}")

                    try:
                        result = await self.session.call_tool(tool_name, tool_args)
                        content = self._format_tool_result(result.content)
                        self.logger.info(f"Tool {tool_name} result: {content[:100]}...")
                        self.messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_use_id,
                                "content": content,
                            }
                        )
                        await self.log_conversation()
                    except Exception as e:
                        self.logger.error(f"Error calling tool {tool_name}: {e}")
                        self.messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_use_id,
                                "content": f"Error using {tool_name}: {str(e)}",
                            }
                        )
                        await self.log_conversation()

            return self.messages

        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            traceback.print_exc()
            return [
                system_message,
                user_message,
                {
                    "role": "assistant",
                    "content": f"I'm sorry, I encountered an error: {str(e)}",
                },
            ]

    async def call_llm(self):
        """Call the Groq LLM with the current messages and tools.
        
        Returns:
            Groq API response
        """
        try:
            self.logger.info("Calling Groq LLM")
            return await self.llm.generate_completion(
                messages=self.messages,
                tools=self.tools
            )
        except Exception as e:
            self.logger.error(f"Error calling Groq LLM: {e}")
            raise

    async def cleanup(self):
        """Clean up resources when shutting down."""
        try:
            await self.exit_stack.aclose()
            self.logger.info("Disconnected from MCP server")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            traceback.print_exc()
            raise

    def _format_tool_result(self, content):
        """Format a tool result into a string.
        
        Args:
            content: The tool result content
            
        Returns:
            str: The formatted result as a string
        """
        if content is None:
            return ""
        
        if isinstance(content, str):
            return content
        
        if isinstance(content, list):
            result = []
            for item in content:
                if hasattr(item, "text"):
                    result.append(item.text)
                elif isinstance(item, dict) and "text" in item:
                    result.append(item["text"])
                else:
                    try:
                        result.append(str(item))
                    except:
                        result.append("[Unprintable item]")
            return "\n".join(result)
        
        if isinstance(content, dict):
            if "text" in content:
                return content["text"]
            try:
                return json.dumps(content, indent=2)
            except:
                pass
        
        try:
            return str(content)
        except:
            return "[Unprintable content]"

    async def log_conversation(self):
        """Log the current conversation to a file."""
        os.makedirs("conversations", exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath = os.path.join("conversations", f"conversation_{timestamp}.json")

        serializable_conversation = []
        for message in self.messages:
            try:
                serializable_message = {"role": message["role"], "content": []}

                if isinstance(message.get("content"), str):
                    serializable_message["content"] = message["content"]
                elif isinstance(message.get("content"), list):
                    serializable_message["content"] = message["content"]
                else:
                    serializable_message["content"] = str(message.get("content", ""))

                if "tool_calls" in message:
                    serializable_message["tool_calls"] = message["tool_calls"]

                if "tool_call_id" in message:
                    serializable_message["tool_call_id"] = message["tool_call_id"]

                serializable_conversation.append(serializable_message)
            except Exception as e:
                self.logger.error(f"Error processing message: {str(e)}")
                self.logger.debug(f"Message content: {message}")
                raise

        try:
            with open(filepath, "w") as f:
                json.dump(serializable_conversation, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Error writing conversation to file: {str(e)}")
            self.logger.debug(f"Serializable conversation: {serializable_conversation}")
            raise