from typing import Optional, List
from contextlib import AsyncExitStack
import traceback

# from utils.logger import logger
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from datetime import datetime
from utils.logger import logger
import json
import os

from langchain_groq import ChatGroq
from utils.message_converter import dict_to_langchain_messages
from utils.tool_converter import dict_to_langchain_tools


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.llm = ChatGroq(
            model_name="llama-3.1-8b-instant",
            temperature=0.7
        )
        self.tools = []
        self.messages = []
        self.logger = logger

    # connect to the MCP server
    async def connect_to_server(self, server_script_path: str, server_script_args: list[str] = None):
        try:
            # Handle npx command for web3-research-mcp
            if server_script_path == "npx":
                command = server_script_path
                args = server_script_args if server_script_args else []
            else:
                is_python = server_script_path.endswith(".py")
                is_js = server_script_path.endswith(".js")
                if not (is_python or is_js):
                    raise ValueError("Server script must be a .py or .js file")

                command = "python" if is_python else "node"
                args = [server_script_path]
                
            server_params = StdioServerParameters(
                command=command, args=args, env=None
            )

            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )

            await self.session.initialize()

            self.logger.info("Connected to MCP server")

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

    # get mcp tool list
    async def get_mcp_tools(self):
        try:
            response = await self.session.list_tools()
            return response.tools
        except Exception as e:
            self.logger.error(f"Error getting MCP tools: {e}")
            raise

        # process query
    async def process_query(self, query: str):
        try:
            self.logger.info(f"Processing query: {query}")
            user_message = {"role": "user", "content": query}
            self.messages = [user_message]

            try:
                response = await self.call_llm()
                
                # Log the raw response format to help with debugging
                self.logger.debug(f"LLM Response type: {type(response)}")
                self.logger.debug(f"LLM Response content type: {type(response.content) if hasattr(response, 'content') else 'No content attribute'}")
                
                # Extract content safely
                if hasattr(response, 'content'):
                    content = response.content
                elif hasattr(response, 'message') and hasattr(response.message, 'content'):
                    content = response.message.content
                else:
                    self.logger.warning("Unexpected response format")
                    content = []
                    
                # Handle response safely
                if isinstance(content, list) and len(content) > 0:
                    # Handle list content (may contain tool calls)
                    if hasattr(content[0], 'type') and content[0].type == "text" and len(content) == 1:
                        # Simple text response
                        text_content = getattr(content[0], 'text', str(content[0]))
                        assistant_message = {
                            "role": "assistant",
                            "content": text_content,
                        }
                        self.messages.append(assistant_message)
                        await self.log_conversation()
                        return self.messages
                    else:
                        # Tool call or complex response
                        assistant_message = {
                            "role": "assistant",
                            "content": response.to_dict()["content"] if hasattr(response, "to_dict") else content,
                        }
                        self.messages.append(assistant_message)
                        await self.log_conversation()
                        
                        # Process any tool calls
                        for item in content:
                            tool_type = getattr(item, 'type', None)
                            if tool_type == "tool_use":
                                # Process tool call
                                tool_name = getattr(item, 'name', '')
                                tool_args = getattr(item, 'input', {})
                                tool_use_id = getattr(item, 'id', '')
                                
                                self.logger.info(f"Calling tool {tool_name} with args {tool_args}")
                                try:
                                    result = await self.session.call_tool(tool_name, tool_args)
                                    self.logger.info(f"Tool {tool_name} result: {str(result)[:100]}...")
                                    
                                    # Add tool result to messages
                                    self.messages.append({
                                        "role": "user",
                                        "content": [{
                                            "type": "tool_result",
                                            "tool_use_id": tool_use_id,
                                            "content": result.content if hasattr(result, 'content') else str(result),
                                        }],
                                    })
                                    await self.log_conversation()
                                except Exception as e:
                                    self.logger.error(f"Error calling tool {tool_name}: {e}")
                                    # Add error message as tool result
                                    self.messages.append({
                                        "role": "user",
                                        "content": [{
                                            "type": "tool_result",
                                            "tool_use_id": tool_use_id,
                                            "content": f"Error: {str(e)}",
                                        }],
                                    })
                                    await self.log_conversation()
                else:
                    # Handle string content or other format
                    assistant_message = {
                        "role": "assistant",
                        "content": str(content) if content else "I'm not sure how to respond to that.",
                    }
                    self.messages.append(assistant_message)
                    await self.log_conversation()
                    
                return self.messages
                
            except Exception as e:
                self.logger.error(f"Error processing response: {e}")
                # Add error message
                self.messages.append({
                    "role": "assistant",
                    "content": f"I encountered an error while processing your request: {str(e)}",
                })
                await self.log_conversation()
                return self.messages

        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            raise

    # call llm
    async def call_llm(self):
        try:
            self.logger.info("Calling LLM")
            
            # Convert dict messages to LangChain message objects using utility function
            langchain_messages = dict_to_langchain_messages(self.messages)
            
            # Format tools for LangChain using utility function
            langchain_tools = dict_to_langchain_tools(self.tools)
            
            # Pass messages directly, with tools formatted properly for OpenAI-compatible chat models
            return await self.llm.ainvoke(
                langchain_messages,
                tools=langchain_tools,
                max_tokens=1000
            )
        except Exception as e:
            self.logger.error(f"Error calling LLM: {e}")
            raise
    # cleanup
    async def cleanup(self):
        try:
            await self.exit_stack.aclose()
            self.logger.info("Disconnected from MCP server")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            traceback.print_exc()
            raise

    async def log_conversation(self):
        os.makedirs("conversations", exist_ok=True)

        serializable_conversation = []

        for message in self.messages:
            try:
                serializable_message = {"role": message["role"], "content": []}

                # Handle both string and list content
                if isinstance(message["content"], str):
                    serializable_message["content"] = message["content"]
                elif isinstance(message["content"], list):
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

                serializable_conversation.append(serializable_message)
            except Exception as e:
                self.logger.error(f"Error processing message: {str(e)}")
                self.logger.debug(f"Message content: {message}")
                raise

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath = os.path.join("conversations", f"conversation_{timestamp}.json")

        try:
            with open(filepath, "w") as f:
                json.dump(serializable_conversation, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Error writing conversation to file: {str(e)}")
            self.logger.debug(f"Serializable conversation: {serializable_conversation}")
            raise