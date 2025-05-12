"""
MCP client implementation for the AgentZer0 bot.
"""
import logging
import json

logger = logging.getLogger(__name__)

class MCPClient:
    """Client for connecting to MCP servers."""
    
    def __init__(self):
        """Initialize the MCP client."""
        self.servers = {}
    
    def register_server(self, name, server_instance):
        """Register an MCP server that the LLM can use.
        
        Args:
            name (str): Name of the server.
            server_instance: Server instance to register.
        """
        logger.info(f"Registering MCP server: {name}")
        self.servers[name] = server_instance
    
    def get_available_tools(self):
        """Get all available tools from registered servers.
        
        Returns:
            list: List of tools in format expected by LLM APIs.
        """
        tools = []
        for server_name, server in self.servers.items():
            server_tools = server.get_tools()
            for tool in server_tools:
                # Format tool for LLM API (Groq/OpenAI format)
                formatted_tool = {
                    "type": "function",
                    "function": {
                        "name": f"{server_name}.{tool['name']}",
                        "description": tool["description"],
                        "parameters": tool["parameters"]
                    }
                }
                tools.append(formatted_tool)
        
        logger.debug(f"Available tools: {json.dumps(tools, indent=2)}")
        return tools
    
    async def execute_tool(self, server_name, tool_name, parameters):
        """Execute a tool on a specific server.
        
        Args:
            server_name (str): Name of the server.
            tool_name (str): Name of the tool to execute.
            parameters (dict): Parameters for the tool.
            
        Returns:
            dict: Result of the tool execution.
        """
        server = self.servers.get(server_name)
        if not server:
            error_msg = f"Server {server_name} not found"
            logger.error(error_msg)
            return {"error": error_msg}
        
        try:
            logger.info(f"Executing tool {server_name}.{tool_name} with parameters: {parameters}")
            result = await server.execute_tool(tool_name, parameters)
            logger.info(f"Tool execution result: {result}")
            return result
        except Exception as e:
            error_msg = f"Error executing tool {server_name}.{tool_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"error": error_msg}