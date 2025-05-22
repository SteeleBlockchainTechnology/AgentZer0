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
import config

# MCP client libraries
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    """Client for MCP servers.
    
    Manages connections to multiple MCP servers, fetches tools, and processes queries using Groq LLM.
    """
    
    def __init__(self):
        """Initialize the MCP client."""
        self.servers = {}
        self.exit_stack = AsyncExitStack()
        self.tools_by_server = {}
        self.all_tools = []
        self.messages: List[Dict[str, Any]] = []
        self.logger = logger
        
        # Initialize Groq language model client
        self.api_key = os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            self.logger.warning("GROQ_API_KEY environment variable is not set")
        self.llm = LanguageModelClient(api_key=self.api_key)

    async def initialize_servers(self):
        """Initialize connections to all configured MCP servers.
        
        Returns:
            bool: True if at least one connection was successful, False otherwise
        """
        # Initialize servers from settings
        if not settings.mcp_servers:
            # If no servers are configured, use the default configuration
            # This maintains backward compatibility
            server_config = config.MCPServerConfig(
                name="default",
                command=settings.default_mcp_command,
                args=settings.default_mcp_args
            )
            settings.mcp_servers.append(server_config)
            self.logger.info(f"Using default MCP server configuration")
        
        # Connect to each configured server
        success = False
        for server_config in settings.mcp_servers:
            if await self.connect_to_server(server_config=server_config):
                success = True
        
        # Combine all tools from all servers - ensure proper format for LLM tools
        self.all_tools = []
        for server_name, tools in self.tools_by_server.items():
            for tool in tools:
                # Clean up tool format to ensure it has all required fields
                tool_with_server = {
                    "name": tool["name"],
                    "description": tool.get("description", f"Tool for {tool['name']}"),
                    "server_name": server_name  # Add server name for routing
                }
                
                # Add input schema if available
                if "input_schema" in tool:
                    tool_with_server["input_schema"] = tool["input_schema"]
                else:
                    # Create a minimal input schema if none exists
                    tool_with_server["input_schema"] = {"type": "object"}
                
                self.all_tools.append(tool_with_server)
        
        # Log tools in debug format
        tool_names = [tool["name"] for tool in self.all_tools]
        self.logger.info(f"All available tools for LLM: {tool_names}")
        
        return success

    async def connect_to_server(self, server_script_path: Optional[str] = None, server_config = None) -> bool:
        """Connect to an MCP server.
        
        Args:
            server_script_path: Optional path to the MCP server script (.py or .js)
                               If not provided, will use settings from config
            server_config: Optional MCPServerConfig object with server configuration
            
        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            # Determine server name and parameters
            if server_config:
                server_name = server_config.name
                command = server_config.command
                args = server_config.args
                self.logger.info(f"Starting MCP server '{server_name}' with: {command} {' '.join(args)}")
                server_params = StdioServerParameters(
                    command=command, args=args, env=None
                )
            elif not server_script_path:
                # For backward compatibility, use default settings
                server_name = "default"
                command = settings.default_mcp_command
                args = settings.default_mcp_args
                self.logger.info(f"Starting MCP server '{server_name}' with: {command} {' '.join(args)}")
                server_params = StdioServerParameters(
                    command=command, args=args, env=None
                )
            else:
                # Use the provided script path (backward compatibility)
                server_name = os.path.basename(server_script_path).split(".")[0]
                is_python = server_script_path.endswith(".py")
                is_js = server_script_path.endswith(".js")
                if not (is_python or is_js):
                    raise ValueError("Server script must be a .py or .js file")
                
                # Set up command based on script type
                command = "python" if is_python else "node"
                self.logger.info(f"Starting MCP server '{server_name}' with: {command} {server_script_path}")
                
                server_params = StdioServerParameters(
                    command=command, args=[server_script_path], env=None
                )

            # Establish connection
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            stdio, client = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(stdio, client)
            )

            await session.initialize()
            self.logger.info(f"Connected to MCP server '{server_name}'")

            # Store server connection info
            self.servers[server_name] = {
                "stdio": stdio,
                "client": client,
                "session": session
            }

            # Fetch and format tools
            mcp_tools = await self.get_mcp_tools(server_name)
            server_tools = [
                {
                    "name": tool.name,
                    "description": tool.description or f"Tool for {tool.name.replace('-', ' ')}",
                    "input_schema": tool.inputSchema,
                }
                for tool in mcp_tools
            ]
            
            # Store tools for this server
            self.tools_by_server[server_name] = server_tools
            
            # Log available tools clearly
            tool_names = [tool["name"] for tool in server_tools]
            self.logger.info(f"Available tools for server '{server_name}': {tool_names}")
            
            # Print detailed tool information for debugging
            for tool in server_tools:
                self.logger.info(f"Tool '{tool['name']}' details (server '{server_name}'):")
                self.logger.info(f"  Description: {tool['description']}")
                if tool.get('input_schema'):
                    self.logger.info(f"  Input schema: {json.dumps(tool['input_schema'], indent=2)[:200]}...")
            
            return True

        except Exception as e:
            self.logger.error(f"Error connecting to MCP server '{server_name if 'server_name' in locals() else 'unknown'}': {e}")
            traceback.print_exc()
            return False

    async def get_mcp_tools(self, server_name="default"):
        """Get the list of available tools from a specific MCP server.
        
        Args:
            server_name: Name of the server to get tools from
            
        Returns:
            List of available tools
        """
        try:
            if server_name not in self.servers:
                raise ValueError(f"Server '{server_name}' not found")
                
            session = self.servers[server_name]["session"]
            response = await session.list_tools()
            return response.tools
        except Exception as e:
            self.logger.error(f"Error getting MCP tools from server '{server_name}': {e}")
            raise

    async def process_query(self, query: str) -> List[Dict[str, Any]]:
        """Process a user query.
        
        Sends query to Groq LLM, processes tool calls, and returns conversation messages.
        Supports both OpenAI-style tool calls and the function-like syntax
        in the format: <function=tool_name{"param":"value"}>
        
        This method supports routing tool calls to the appropriate server based on the
        server_name attribute added to each tool.
        
        Args:
            query: The user's query text
            
        Returns:
            List[Dict[str, Any]]: The conversation messages
        """
        try:
            self.logger.info(f"Processing query: {query}")
            
            # Debug log to check if tools are available
            if not self.all_tools:
                self.logger.warning("No tools available for this query. Make sure initialize_servers() was called.")
            else:
                self.logger.info(f"Available tools for query: {', '.join(t['name'] for t in self.all_tools)}")
                for tool in self.all_tools:
                    self.logger.debug(f"Tool details - Name: {tool['name']}, Description: {tool.get('description', 'No description')}")
            
            # Initialize conversation with user message
            user_message = {"role": "user", "content": query}
            self.messages = [user_message]
            
            # Track if we've had a failed tool call
            had_tool_failure = False
            have_function_text = False
            
            # Start conversation loop
            max_iterations = 15  # Limit iterations to avoid infinite loops
            for iteration in range(max_iterations):
                try:
                    # Call LLM for response
                    response = await self.llm.generate_completion(
                        messages=self.messages,
                        tools=self.all_tools
                    )
                    
                    # Extract content from response
                    assistant_content = response.choices[0].message.content or ""
                    
                    # Check if the response is just a function call
                    function_patterns = [
                        r'^<function=(\w+)\{(.*?)\}>$',
                        r'^<function=(\w+)\((.*?)\)>$',
                        r'^<function=(\w+)\((.*?)\)</function>$',
                        r'^function=(\w+)\((.*?)\)',
                        r'^function=(\w+)\{(.*?)\}'
                    ]
                    
                    is_just_function_text = False
                    for pattern in function_patterns:
                        if re.match(pattern, assistant_content.strip()):
                            is_just_function_text = True
                            have_function_text = True
                            self.logger.info(f"Response appears to be just a function call: {assistant_content}")
                            break
                    
                    # If the response is just a function call, skip adding it as a message
                    if is_just_function_text:
                        self.logger.info("Not adding function call text as a message, processing as a tool call instead")
                    else:
                        # Check if the response has official tool calls
                        has_tool_calls = False
                        if hasattr(response.choices[0].message, "tool_calls") and response.choices[0].message.tool_calls:
                            has_tool_calls = True
                            
                            # Create a clean version of the assistant message without tool calls embedded in content
                            clean_content = re.sub(r'<function=\w+\{.*?\}>', '', assistant_content).strip()
                            
                            # If we've had tool failures, only add the content to avoid API errors
                            if had_tool_failure:
                                assistant_message = {
                                    "role": "assistant", 
                                    "content": clean_content or "I'll try to get that information for you."
                                }
                            else:
                                # First tool call - include the tool calls in the message
                                assistant_message = {
                                    "role": "assistant",
                                    "content": clean_content,
                                    "tool_calls": response.choices[0].message.tool_calls
                                }
                            
                            self.messages.append(assistant_message)
                            await self.log_conversation()
                            
                            # Process each tool call
                            all_tools_succeeded = True
                            have_successful_results = False
                            
                            for tool_call in response.choices[0].message.tool_calls:
                                tool_name = tool_call.function.name
                                try:
                                    # Parse the arguments
                                    tool_args_str = tool_call.function.arguments
                                    
                                    # Fix common formatting issues
                                    if tool_args_str.startswith("{"): 
                                        # Already valid JSON format
                                        pass
                                    elif tool_args_str.startswith("\"") or tool_args_str.startswith("'"):
                                        # String that might need wrapping
                                        tool_args_str = "{\"query\": " + tool_args_str + "}"
                                    else:
                                        # Wrap in curly braces if not already present
                                        tool_args_str = '{' + tool_args_str + '}'
                                    
                                    # Clean up any potential issues
                                    tool_args_str = tool_args_str.replace("\\\"", "\"").replace("\\\'", "'")
                                    
                                    # Try to parse the arguments 
                                    try:
                                        tool_args = json.loads(tool_args_str)
                                    except json.JSONDecodeError as e:
                                        # If parsing fails, try fixing common JSON syntax errors
                                        self.logger.warning(f"Failed to parse tool args: {e}. Attempting to fix.")
                                        # Try to add quotes around unquoted keys
                                        fixed_str = re.sub(r'(\w+):', r'"\1":', tool_args_str)
                                        tool_args = json.loads(fixed_str)
                                    
                                    # Find which server has this tool
                                    server_name = self._find_server_for_tool(tool_name)
                                    if not server_name:
                                        raise ValueError(f"Tool '{tool_name}' not found in any connected server")
                                    
                                    # Call the tool on the appropriate server
                                    self.logger.info(f"Calling tool {tool_name} on server '{server_name}' with args {tool_args}")
                                    session = self.servers[server_name]["session"]
                                    
                                    try:
                                        result = await session.call_tool(tool_name, tool_args)
                                        # Format tool result
                                        content = self._format_tool_result(result.content)
                                        self.logger.info(f"Tool {tool_name} on server '{server_name}' result received: {content[:100] if content else 'Empty'}...")
                                        
                                        # Check if we got a successful price or other useful data
                                        if content and not content.startswith("Error") and (
                                            ("price" in content.lower()) or 
                                            ("Current price" in content) or 
                                            ("value" in content.lower() and any(crypto in content.lower() for crypto in ["btc", "bitcoin", "eth", "ethereum", "bnb", "sol", "solana", "xrp"])) or
                                            ("search results" in content.lower()) or
                                            ("research" in content.lower())
                                        ):
                                            have_successful_results = True
                                            self.logger.info(f"Successfully retrieved data: {content[:100]}...")
                                            
                                    except Exception as tool_error:
                                        self.logger.error(f"Error executing tool {tool_name}: {tool_error}")
                                        # Handle tool execution error specifically
                                        content = f"Error: The {tool_name} tool encountered an error. Please try a different approach. Error details: {str(tool_error)}"
                                        all_tools_succeeded = False
                                    
                                    # After first iteration with failed tools, don't include tool_call_id in further messages
                                    if had_tool_failure:
                                        tool_result_message = {
                                            "role": "user",
                                            "content": f"Tool {tool_name} returned: {content}"
                                        }
                                    else:
                                        # First attempt - include proper tool format
                                        tool_result_message = {
                                            "role": "tool",
                                            "tool_call_id": tool_call.id,
                                            "name": tool_name,
                                            "content": content
                                        }
                                    
                                    self.messages.append(tool_result_message)
                                    await self.log_conversation()
                                except Exception as e:
                                    self.logger.error(f"Error handling tool call {tool_name}: {e}")
                                    all_tools_succeeded = False
                                    
                                    # After first iteration with failed tools, don't include tool_call_id in further messages
                                    if had_tool_failure:
                                        tool_error_message = {
                                            "role": "user",
                                            "content": f"Error using tool {tool_name}: {str(e)}"
                                        }
                                    else:
                                        # First attempt - include proper tool format
                                        tool_error_message = {
                                            "role": "tool",
                                            "tool_call_id": tool_call.id,
                                            "name": tool_name,
                                            "content": f"Error: {str(e)}"
                                        }
                                    
                                    self.messages.append(tool_error_message)
                                    await self.log_conversation()
                            
                            # Update tool failure flag
                            if not all_tools_succeeded:
                                had_tool_failure = True
                                
                            # If we have successful results, create a final answer
                            if have_successful_results:
                                # Get the most recent successful tool result
                                successful_result = None
                                for msg in reversed(self.messages):
                                    if msg.get("role") == "tool" and "Error" not in msg.get("content", ""):
                                        successful_result = msg.get("content")
                                        break
                                
                                if successful_result:
                                    # Generate a final response with the data we found
                                    final_response = {
                                        "role": "assistant",
                                        "content": successful_result
                                    }
                                    self.messages.append(final_response)
                                    self.logger.info(f"Breaking loop with successful result: {successful_result}")
                                    break
                            
                            # Continue the conversation if there were tool calls
                            continue
                        
                        # Check for function calls in text - whether we added a message or not
                        function_matches = []
                        
                        # Only check for traditional function matches if we don't have official tool calls
                        # Or if the response is just a function text
                        if not has_tool_calls or is_just_function_text:
                            # Try different function call patterns
                            patterns = [
                                r'<function=(\w+)\{(.*?)\}>', # Original format
                                r'<function=(\w+)\((.*?)\)>', # Format with parentheses
                                r'<function=(\w+)\((.*?)\)</function>', # Format with closing tag
                                r'function=(\w+)\((.*?)\)', # Format without brackets
                                r'function=(\w+)\{(.*?)\}', # Format without brackets with curly braces
                            ]
                            
                            for pattern in patterns:
                                matches = re.findall(pattern, assistant_content)
                                if matches:
                                    function_matches.extend(matches)
                                    self.logger.info(f"Found function call using pattern {pattern}: {matches}")
                        
                        # If no function calls are found, add the assistant message and break
                        if not function_matches:
                            # Only add a message if we haven't already added one
                            if not is_just_function_text:
                                assistant_message = {
                                    "role": "assistant",
                                    "content": assistant_content,
                                }
                                self.messages.append(assistant_message)
                                await self.log_conversation()
                            break
                        
                        # Add the assistant message with the function call only if we haven't identified it as just a function call
                        if not is_just_function_text:
                            assistant_message = {
                                "role": "assistant",
                                "content": assistant_content,
                            }
                            self.messages.append(assistant_message)
                            await self.log_conversation()
                        
                        # Process each function call from text
                        all_tools_succeeded = True
                        have_successful_results = False
                        
                        for tool_name, tool_args_str in function_matches:
                            self.logger.info(f"Processing text function call: {tool_name} with args {tool_args_str}")
                            
                            try:
                                # Handle the tool call logic
                                # Parse arguments, find server, execute tool call, etc.
                                # [Code to process the function call]
                                
                                # Parse the JSON arguments - ensure proper formatting
                                tool_args_str = tool_args_str.strip()
                                
                                # Fix common formatting issues
                                if tool_args_str.startswith("{"): 
                                    # Already valid JSON format
                                    pass
                                elif tool_args_str.startswith("\"") or tool_args_str.startswith("'"):
                                    # String that might need wrapping
                                    tool_args_str = "{\"query\": " + tool_args_str + "}"
                                else:
                                    # Wrap in curly braces if not already present
                                    tool_args_str = '{' + tool_args_str + '}'
                                
                                # Clean up any potential issues
                                tool_args_str = tool_args_str.replace("\\\"", "\"").replace("\\\'", "'")
                                
                                # Try to parse the arguments 
                                try:
                                    tool_args = json.loads(tool_args_str)
                                except json.JSONDecodeError as e:
                                    # If parsing fails, try fixing common JSON syntax errors
                                    self.logger.warning(f"Failed to parse tool args: {e}. Attempting to fix.")
                                    # Try to add quotes around unquoted keys
                                    fixed_str = re.sub(r'(\w+):', r'"\1":', tool_args_str)
                                    tool_args = json.loads(fixed_str)
                                
                                # Find which server has this tool
                                server_name = self._find_server_for_tool(tool_name)
                                if not server_name:
                                    raise ValueError(f"Tool '{tool_name}' not found in any connected server")
                                
                                # Call the tool on the appropriate server
                                self.logger.info(f"Calling tool {tool_name} on server '{server_name}' with args {tool_args}")
                                session = self.servers[server_name]["session"]
                                
                                try:
                                    result = await session.call_tool(tool_name, tool_args)
                                    # Format tool result
                                    content = self._format_tool_result(result.content)
                                    self.logger.info(f"Tool {tool_name} on server '{server_name}' result received: {content[:100] if content else 'Empty'}...")
                                    
                                    # Check if we got a successful result
                                    if content and not content.startswith("Error"):
                                        have_successful_results = True
                                        self.logger.info(f"Successfully retrieved data: {content}")
                                    
                                except Exception as tool_error:
                                    self.logger.error(f"Error executing tool {tool_name}: {tool_error}")
                                    # Handle tool execution error specifically
                                    content = f"Error: The {tool_name} tool encountered an error. Please try a different approach. Error details: {str(tool_error)}"
                                    all_tools_succeeded = False
                                
                                # Add the tool result as a message
                                tool_result_message = {
                                    "role": "user",
                                    "content": f"Tool '{tool_name}' returned: {content}"
                                }
                                self.messages.append(tool_result_message)
                                await self.log_conversation()
                                
                                # If this was the only function and directly translated to a result, let's just return it
                                if is_just_function_text and have_successful_results:
                                    final_message = {
                                        "role": "assistant",
                                        "content": content
                                    }
                                    self.messages.append(final_message)
                                    self.logger.info(f"Adding final message with direct tool result: {content[:100] if content else 'Empty'}...")
                                    return self.messages
                                
                            except Exception as e:
                                self.logger.error(f"Error processing function call {tool_name}: {e}")
                                all_tools_succeeded = False
                                tool_error_message = {
                                    "role": "user",
                                    "content": f"Error using tool '{tool_name}': {str(e)}"
                                }
                                self.messages.append(tool_error_message)
                                await self.log_conversation()
                        
                        # Update tool failure flag
                        if not all_tools_succeeded:
                            had_tool_failure = True
                        
                        # Continue the conversation if we're still going
                        continue
                    
                except Exception as e:
                    self.logger.error(f"Error in conversation loop: {e}")
                    # Add error message to conversation
                    error_message = {
                        "role": "assistant",
                        "content": f"I encountered an error processing your request. Let me try to answer without using tools: {str(e)}"
                    }
                    self.messages.append(error_message)
                    
                    # Try a simple response without tools
                    try:
                        # Make one final attempt without tools
                        simple_messages = self.messages.copy()
                        # Remove any problematic messages
                        simple_messages = [m for m in simple_messages if m.get("role") in ["user", "assistant", "system"]]
                        
                        response = await self.llm.generate_completion(
                            messages=simple_messages,
                            tools=None  # No tools
                        )
                        self.messages.append({
                            "role": "assistant",
                            "content": response.choices[0].message.content
                        })
                        break
                    except Exception as final_error:
                        self.logger.error(f"Final attempt failed: {final_error}")
                        self.messages.append({
                            "role": "assistant",
                            "content": "I'm sorry, I'm having trouble processing your request right now. Please try again later."
                        })
                        break
            
            # If we reach maximum iterations, add a final response
            if iteration == max_iterations - 1:
                # Check if we have any successful tool results we can use
                last_successful_content = None
                for msg in reversed(self.messages):
                    # Find the last tool message that doesn't contain an error
                    if msg.get("role") == "tool" and "Error" not in msg.get("content", ""):
                        last_successful_content = msg.get("content")
                        break
                
                # Also check for any research or search results even if not from a tool message
                if not last_successful_content:
                    for msg in reversed(self.messages):
                        content = msg.get("content", "")
                        if isinstance(content, str) and ("search results" in content.lower() or "research" in content.lower()):
                            last_successful_content = content
                            break
                
                if last_successful_content:
                    # If we have a successful result, use it instead of generic message
                    self.messages.append({
                        "role": "assistant",
                        "content": f"{last_successful_content}"
                    })
                else:
                    # If no successful results at all, use generic fallback
                    self.messages.append({
                        "role": "assistant",
                        "content": "I've made several attempts to retrieve information but encountered some issues. Could you provide more details about what you're looking for?"
                    })

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
            self.logger.info("Disconnected from all MCP servers")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            traceback.print_exc()
            raise
            
    def _find_server_for_tool(self, tool_name):
        """Find which server provides a specific tool.
        
        Args:
            tool_name: Name of the tool to find
            
        Returns:
            str: Name of the server that provides the tool, or None if not found
        """
        for server_name, tools in self.tools_by_server.items():
            for tool in tools:
                if tool["name"] == tool_name:
                    return server_name
        return None

    def _format_tool_result(self, content):
        """Format a tool result into a string.
        
        Args:
            content: The tool result content
            
        Returns:
            str: The formatted result as a string
        """
        if content is None:
            return ""
        
        # If the content is already a string, return it
        if isinstance(content, str):
            return content
        
        # Handle error responses specifically
        if isinstance(content, dict) and content.get('type') == 'error':
            error_text = content.get('text', 'Unknown error')
            self.logger.warning(f"Tool returned error: {error_text}")
            return f"Error: {error_text}"
        
        # Handle lists of content
        if isinstance(content, list):
            result = []
            for item in content:
                if isinstance(item, dict) and item.get('type') == 'error':
                    # Handle error responses in list
                    error_text = item.get('text', 'Unknown error')
                    self.logger.warning(f"Tool returned error in list: {error_text}")
                    result.append(f"Error: {error_text}")
                elif hasattr(item, "text"):
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
        
        # As a last resort, try to convert to string
        try:
            return str(content)
        except:
            return "[Unprintable content]"

    async def log_conversation(self):
        """Log the current conversation to a file."""
        os.makedirs("conversations", exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath = os.path.join("conversations", f"conversation_{timestamp}.json")

        # Define a simple JSON encoder here to avoid import issues
        class SimpleJsonEncoder(json.JSONEncoder):
            """Simple JSON encoder that handles objects that aren't JSON serializable"""
            def default(self, obj):
                try:
                    return super().default(obj)
                except TypeError:
                    try:
                        return str(obj)
                    except:
                        return "[Object not serializable]"

        serializable_conversation = []
        for message in self.messages:
            try:
                serializable_message = {"role": message.get("role", "unknown")}

                # Handle content field
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
                            serializable_message["content"].append(str(item))
                else:
                    serializable_message["content"] = str(message.get("content", ""))

                # Handle tool_calls field - convert complex objects to strings
                if "tool_calls" in message:
                    try:
                        # Convert tool_calls to a basic dictionary or string
                        if hasattr(message["tool_calls"], "__iter__"):
                            tool_calls_list = []
                            for call in message["tool_calls"]:
                                if hasattr(call, "__dict__"):
                                    tool_calls_list.append(call.__dict__)
                                else:
                                    tool_calls_list.append(str(call))
                            serializable_message["tool_calls"] = tool_calls_list
                        else:
                            serializable_message["tool_calls"] = str(message["tool_calls"])
                    except Exception as e:
                        self.logger.warning(f"Could not serialize tool_calls: {e}")
                        serializable_message["tool_calls"] = str(message["tool_calls"])

                # Handle other special fields
                if "tool_call_id" in message:
                    serializable_message["tool_call_id"] = message["tool_call_id"]

                if "name" in message:
                    serializable_message["name"] = message["name"]

                serializable_conversation.append(serializable_message)
            except Exception as e:
                self.logger.error(f"Error processing message: {str(e)}")
                self.logger.debug(f"Message content type: {type(message.get('content'))}")
                # Add a placeholder for the problematic message
                serializable_conversation.append({
                    "role": message.get("role", "unknown"),
                    "content": f"[Error serializing message: {str(e)}]"
                })

        try:
            with open(filepath, "w") as f:
                json.dump(serializable_conversation, f, indent=2, cls=SimpleJsonEncoder)
        except Exception as e:
            self.logger.error(f"Error writing conversation to file: {str(e)}")
            # Try to write a simplified version
            try:
                simplified = [{"role": m.get("role", "unknown"), "content": str(m.get("content", ""))} 
                             for m in self.messages]
                with open(filepath, "w") as f:
                    json.dump(simplified, f, indent=2)
            except Exception as e2:
                self.logger.error(f"Even simplified serialization failed: {str(e2)}")