from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack
import traceback
import json
import os
import re
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

    async def connect_to_server(self, server_script_path: Optional[str] = None) -> bool:
        """Connect to the MCP server.
        
        Args:
            server_script_path: Optional path to the MCP server script (.py or .js)
                               If not provided, will use settings from config
            
        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            # If no script path provided, use the settings to run web3-research-mcp via npx
            if not server_script_path:
                # Get configuration from settings
                command = settings.mcp_command  # Should be "npx"
                args = settings.mcp_args       # Should be ["-y", "web3-research-mcp@latest"]
                
                self.logger.info(f"Starting MCP server with: {command} {' '.join(args)}")
                
                # Set up server parameters for npx command
                server_params = StdioServerParameters(
                    command=command, args=args, env=None
                )
            else:
                # Use the provided script path (backward compatibility)
                is_python = server_script_path.endswith(".py")
                is_js = server_script_path.endswith(".js")
                if not (is_python or is_js):
                    raise ValueError("Server script must be a .py or .js file")
                
                # Set up command based on script type
                command = "python" if is_python else "node"
                self.logger.info(f"Starting MCP server with: {command} {server_script_path}")
                
                server_params = StdioServerParameters(
                    command=command, args=[server_script_path], env=None
                )

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
                    "input_schema": tool.inputSchema,
                }
                for tool in mcp_tools
            ]
            
            # Log available tools clearly
            tool_names = [tool["name"] for tool in self.tools]
            self.logger.info(f"Available tools: {tool_names}")
            
            # Print detailed tool information for debugging
            for tool in self.tools:
                self.logger.info(f"Tool '{tool['name']}' details:")
                self.logger.info(f"  Description: {tool['description']}")
                if tool.get('input_schema'):
                    self.logger.info(f"  Input schema: {json.dumps(tool['input_schema'], indent=2)[:200]}...")
            
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
        Instead of using the Groq tool_calls format, this will parse function-like syntax
        in the format: <function=tool_name{"param":"value"}>
        
        Args:
            query: The user's query text
            
        Returns:
            List[Dict[str, Any]]: The conversation messages
        """
        try:
            self.logger.info(f"Processing query: {query}")
            
            # Initialize conversation with user message
            user_message = {"role": "user", "content": query}
            self.messages = [user_message]

            # Start conversation loop
            while True:
                # Call LLM for response
                response = await self.llm.generate_completion(
                    messages=self.messages,
                    tools=self.tools
                )
                
                # Extract content from response
                assistant_content = response.choices[0].message.content or ""
                
                # Check if the response contains function calls
                function_pattern = r'<function=(\w+)\{(.*?)\}>'
                function_matches = re.findall(function_pattern, assistant_content)
                
                # If no function calls are found, add the assistant message and break
                if not function_matches:
                    assistant_message = {
                        "role": "assistant",
                        "content": assistant_content,
                    }
                    self.messages.append(assistant_message)
                    await self.log_conversation()
                    break
                
                # Add the assistant message with the function call
                assistant_message = {
                    "role": "assistant",
                    "content": assistant_content,
                }
                self.messages.append(assistant_message)
                await self.log_conversation()
                
                # Process each function call
                for tool_name, tool_args_str in function_matches:
                    self.logger.info(f"Found function call: {tool_name} with args {tool_args_str}")
                    
                    try:
                        # Parse the JSON arguments - ensure proper formatting
                        # Wrap in curly braces if not already present
                        if not tool_args_str.strip().startswith('{'):
                            tool_args_str = '{' + tool_args_str + '}'
                        
                        tool_args = json.loads(tool_args_str)
                        
                        # Call the tool
                        self.logger.info(f"Calling tool {tool_name} with args {tool_args}")
                        result = await self.session.call_tool(tool_name, tool_args)
                        
                        # Format tool result
                        content = self._format_tool_result(result.content)
                        self.logger.info(f"Tool {tool_name} result received")
                        
                        # Add the tool result as a user message (similar to the working implementation)
                        tool_result_message = {
                            "role": "user",
                            "content": f"Tool '{tool_name}' returned: {content}"
                        }
                        self.messages.append(tool_result_message)
                        await self.log_conversation()
                    except Exception as e:
                        self.logger.error(f"Error calling tool {tool_name}: {e}")
                        tool_error_message = {
                            "role": "user",
                            "content": f"Error using tool '{tool_name}': {str(e)}"
                        }
                        self.messages.append(tool_error_message)
                        await self.log_conversation()

            return self.messages

        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            traceback.print_exc()
            
            # Create fallback error message
            error_message = {
                "role": "assistant",
                "content": f"I'm sorry, I encountered an error: {str(e)}",
            }
            
            # Ensure we have at least a user message
            if not self.messages or not any(msg.get("role") == "user" for msg in self.messages):
                self.messages = [user_message, error_message]
            else:
                self.messages.append(error_message)
                
            return self.messages

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
                serializable_message = {"role": message["role"]}

                if isinstance(message.get("content"), str):
                    serializable_message["content"] = message["content"]
                elif isinstance(message.get("content"), list):
                    serializable_message["content"] = []
                    for item in message["content"]:
                        if hasattr(item, "to_dict"):
                            serializable_message["content"].append(item.to_dict())
                        elif hasattr(item, "dict"):
                            serializable_message["content"].append(item.dict())
                        elif hasattr(item, "model_dump"):
                            serializable_message["content"].append(item.model_dump())
                        else:
                            serializable_message["content"].append(item)
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