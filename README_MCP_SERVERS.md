# Multiple MCP Server Configuration

This document explains how to configure and use multiple MCP servers with AgentZer0.

## Overview

AgentZer0 now supports connecting to multiple MCP (Machine Cognition Protocol) servers simultaneously. This allows you to:

- Distribute workload across multiple servers
- Access different sets of tools from specialized servers
- Create redundancy for improved reliability

## Configuration

Multiple MCP servers are configured in the `config/settings.py` file. Each server requires a unique name, command, and arguments.

### Example Configuration

To add multiple MCP servers, modify the `settings.py` file as follows:

```python
# Add a default MCP server
settings.mcp_servers.append(MCPServerConfig(
    name="default",
    command="npx",
    args=["-y", "web3-research-mcp@latest"]
))

# Add another MCP server with different configuration
settings.mcp_servers.append(MCPServerConfig(
    name="custom_server",
    command="python",
    args=["path/to/custom_mcp_server.py"]
))

# Add a third MCP server running a JavaScript implementation
settings.mcp_servers.append(MCPServerConfig(
    name="js_server",
    command="node",
    args=["path/to/js_server.js"]
))
```

### Configuration Parameters

- `name`: A unique identifier for the server (used for routing tool calls)
- `command`: The command to run the server (e.g., "npx", "python", "node")
- `args`: A list of arguments for the command

## How It Works

When the application starts:

1. The system connects to all configured MCP servers
2. Tools from all servers are collected and made available to the LLM
3. Tool calls are automatically routed to the appropriate server

## Backward Compatibility

For backward compatibility, if no servers are explicitly configured, the system will automatically create a default server using the configuration from `default_mcp_command` and `default_mcp_args`.

The original `mcp_command` and `mcp_args` properties are still available as properties that return the default values.

## Troubleshooting

If you encounter issues with multiple MCP servers:

1. Check the logs for connection errors
2. Verify that each server has a unique name
3. Ensure that all server commands and arguments are correct
4. Check that the servers are accessible and running properly

## Advanced Usage

### Tool Routing

Tool calls are automatically routed to the appropriate server based on the tool name. If multiple servers provide a tool with the same name, the first server that was configured will be used.

### Server Management

The `MCPClient` class provides methods for managing server connections:

- `initialize_servers()`: Connects to all configured servers
- `connect_to_server(server_config=...)`: Connects to a specific server
- `cleanup()`: Disconnects from all servers
