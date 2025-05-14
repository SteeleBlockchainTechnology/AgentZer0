from typing import Optional, List, Dict, Any
import os
import json
import asyncio
import traceback
from datetime import datetime
import re

# Import application components
from utils.logger import logger
from client.language_model import LanguageModelClient

# MCP client libraries (if using a custom package)
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Import application settings
from config.settings import settings


class MCPClient:
    """Client for the MCP server.
    
    This client manages the connection to the MCP server, fetches tools, and processes queries.
    """
    
    def __init__(self):
        """Initialize the MCP client."""
        # Set up server connection variables
        self.session = None
        self.stdio = None
        self.write = None
        self.exit_stack = None
        self.tools = []
        self.messages = []
        self.logger = logger
        
        # Create language model client
        self.api_key = os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            self.logger.warning("GROQ_API_KEY environment variable is not set")
        self.language_model = LanguageModelClient(api_key=self.api_key)
    
    async def connect_to_server(self, _=None):
        """Connect to the MCP server.
        
        Args:
            _: Ignored parameter (for backward compatibility)
            
        Returns:
            bool: True if connection was successful
        """
        # Import AsyncExitStack here to avoid issues in environments without it
        from contextlib import AsyncExitStack
        self.exit_stack = AsyncExitStack()
        
        try:
            # Set up the command to start the MCP server
            server_params = StdioServerParameters(
                command=settings.mcp_command,
                args=settings.mcp_args,
                env=None  # Use the current environment
            )
            
            # Log the command being executed
            self.logger.info(f"Starting MCP server with: {settings.mcp_command} {' '.join(settings.mcp_args)}")
            
            # Establish the connection
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.stdio, self.write = stdio_transport
            
            # Initialize the MCP session
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )
            await self.session.initialize()
            
            self.logger.info("Connected to web3-research-mcp server")
            
            # Fetch available tools
            mcp_tools = await self.get_mcp_tools()
            
            # Format tools for use with the language model
            self.tools = [
                {
                    "name": tool.name,
                    "description": tool.description or f"Tool for {tool.name.replace('-', ' ')}",
                    "inputSchema": tool.inputSchema,
                }
                for tool in mcp_tools
            ]
            
            # Log available tools
            tool_names = [tool["name"] for tool in self.tools]
            self.logger.info(f"Available tools: {tool_names}")
            
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
    
    async def process_tool_call(self, tool_call):
        """Process a single tool call from the LLM.
        
        Args:
            tool_call: The tool call from the LLM
            
        Returns:
            dict: The tool response message
        """
        tool_name = tool_call.function.name
        tool_args_str = tool_call.function.arguments
        tool_call_id = tool_call.id
        
        # Parse the tool arguments
        try:
            tool_args = json.loads(tool_args_str)
        except json.JSONDecodeError:
            tool_args = {}
        
        self.logger.info(f"Calling tool {tool_name} with args {tool_args}")
        
        try:
            # Call the tool via the MCP session
            result = await self.session.call_tool(tool_name, tool_args)
            
            # Format the result
            content = self._format_tool_result(result.content)
            self.logger.info(f"Tool {tool_name} result: {content[:100]}...")
            
            # Return the tool response message
            return {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": content,
            }
        except Exception as e:
            self.logger.error(f"Error calling tool {tool_name}: {e}")
            # Return an error message
            return {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": f"Error using {tool_name}: {str(e)}",
            }
    
    def _format_tool_result(self, content):
        """Format a tool result into a string.
        
        Args:
            content: The tool result content
            
        Returns:
            str: The formatted result as a string
        """
        if content is None:
            return ""
        
        # Handle string content
        if isinstance(content, str):
            return content
        
        # Handle list content
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
        
        # Handle dictionary content
        if isinstance(content, dict):
            if "text" in content:
                return content["text"]
            try:
                return json.dumps(content, indent=2)
            except:
                pass
        
        # Fallback: convert to string
        try:
            return str(content)
        except:
            return "[Unprintable content]"
    
    async def process_query(self, query: str) -> List[Dict[str, Any]]:
        """Process a user query.
        
        This method:
        1. Sends the query to the language model
        2. Processes any tool calls from the model
        3. Sends the tool results back to the model
        4. Returns the final response
        
        Args:
            query: The user's query text
            
        Returns:
            List[Dict[str, Any]]: The conversation messages
        """
        try:
            self.logger.info(f"Processing query: {query}")
            
            # Initialize conversation with system message and user query
            system_message = {
                "role": "system",
                "content": (
                    "You are a helpful assistant with expertise in cryptocurrency research. "
                    "You have access to web3-research-mcp tools that can help you gather information "
                    "about various cryptocurrency tokens, market data, and blockchain projects."
                ),
            }
            user_message = {"role": "user", "content": query}
            self.messages = [system_message, user_message]
            
            # Track iterations to prevent infinite loops
            max_iterations = 3
            for iteration in range(max_iterations):
                self.logger.info(f"Processing iteration {iteration + 1}")
                
                # Call the language model
                response = await self.language_model.generate_completion(
                    messages=self.messages,
                    tools=self.tools
                )
                
                # Extract the assistant's message
                message = response.choices[0].message
                
                # Check if the message has tool calls
                if hasattr(message, "tool_calls") and message.tool_calls:
                    # Process tool calls
                    assistant_message = {
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": message.tool_calls,
                    }
                    self.messages.append(assistant_message)
                    
                    # Process each tool call in parallel
                    tasks = [self.process_tool_call(tool_call) for tool_call in message.tool_calls]
                    tool_responses = await asyncio.gather(*tasks)
                    
                    # Add tool responses to the conversation
                    self.messages.extend(tool_responses)
                    
                    # If we've reached the max iterations, add a final response
                    if iteration == max_iterations - 1:
                        # Create a summary response
                        tool_results = [msg["content"] for msg in tool_responses]
                        summary = "Based on my research: " + " ".join(tool_results)
                        final_message = {
                            "role": "assistant",
                            "content": self._clean_response(summary),
                        }
                        self.messages.append(final_message)
                        break
                    
                    # Otherwise, continue iterating
                else:
                    # No tool calls, just add the response and break
                    assistant_message = {
                        "role": "assistant",
                        "content": self._clean_response(message.content or ""),
                    }
                    self.messages.append(assistant_message)
                    break
            
            # Log the conversation
            await self.log_conversation()
            
            return self.messages
        
        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            traceback.print_exc()
            # Return a minimal conversation with an error message
            return [
                system_message,
                user_message,
                {
                    "role": "assistant",
                    "content": f"I'm sorry, I encountered an error: {str(e)}",
                },
            ]
    
    def _clean_response(self, response):
        """Clean a response to make it more readable.
        
        This removes any function call syntax or other artifacts.
        
        Args:
            response: The response text from the LLM
            
        Returns:
            str: The cleaned response
        """
        if not response:
            return ""
        
        # Remove function call syntax
        response = re.sub(r'<function=.*?>.*?(?:</function>)?', '', response)
        
        # Remove extra whitespace
        response = re.sub(r'\s+', ' ', response).strip()
        
        return response
    
    async def cleanup(self):
        """Clean up resources when shutting down."""
        if self.exit_stack:
            await self.exit_stack.aclose()
            self.logger.info("Disconnected from MCP server")
    
    async def log_conversation(self):
        """Log the current conversation to a file."""
        # Create the conversations directory if it doesn't exist
        os.makedirs("conversations", exist_ok=True)
        
        # Generate timestamp for the log file
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath = os.path.join("conversations", f"conversation_{timestamp}.json")
        
        try:
            # Convert messages to a serializable format
            serializable_messages = []
            for message in self.messages:
                serializable_message = {"role": message["role"]}
                
                # Process the content
                if isinstance(message.get("content"), str):
                    serializable_message["content"] = message["content"]
                else:
                    serializable_message["content"] = str(message.get("content", ""))
                
                # Process tool_calls if present
                if "tool_calls" in message:
                    serializable_message["tool_calls"] = []
                    for tool_call in message["tool_calls"]:
                        if hasattr(tool_call, "model_dump"):
                            serializable_message["tool_calls"].append(tool_call.model_dump())
                        else:
                            serializable_message["tool_calls"].append(str(tool_call))
                
                # Add tool_call_id if present
                if "tool_call_id" in message:
                    serializable_message["tool_call_id"] = message["tool_call_id"]
                
                serializable_messages.append(serializable_message)
            
            # Write to the log file
            with open(filepath, "w") as f:
                json.dump(serializable_messages, f, indent=2)
            
        except Exception as e:
            self.logger.error(f"Error logging conversation: {e}")
            # Don't raise - this is a non-critical operation