# test_local_mcp.py
# A simple script to test your local web3-research-mcp installation

import asyncio
import os
import json
import sys
from contextlib import AsyncExitStack

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("Error: MCP libraries not found. Please install the MCP package.")
    print("You can install it with: pip install mcp")
    sys.exit(1)

from config.settings import settings

async def test_local_mcp():
    """Test the local MCP installation"""
    exit_stack = AsyncExitStack()
    
    try:
        print(f"\nTesting MCP with command: {settings.mcp_command} {' '.join(settings.mcp_args)}")
        
        # Set up server parameters based on settings
        server_params = StdioServerParameters(
            command=settings.mcp_command, 
            args=settings.mcp_args, 
            env=None
        )
        
        # Establish connection
        stdio_transport = await exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        stdio, client = stdio_transport
        session = await exit_stack.enter_async_context(
            ClientSession(stdio, client)
        )

        await session.initialize()
        print("✅ Successfully connected to local MCP server")
        
        # List available tools
        tools_response = await session.list_tools()
        tools = tools_response.tools
        
        print(f"\n=== Available Tools ({len(tools)}) ===")
        for i, tool in enumerate(tools):
            print(f"\n[{i+1}] Tool: {tool.name}")
            print(f"    Description: {tool.description or 'No description'}")
            
            if tool.inputSchema:
                print(f"    Required Parameters: {tool.inputSchema.get('required', [])}")
                print(f"    Parameters:")
                for param, details in tool.inputSchema.get("properties", {}).items():
                    print(f"      - {param}: {details.get('type', 'unknown')} ({details.get('description', 'No description')})")
        
        # Test search tool if available
        search_tool = next((t for t in tools if t.name == "search"), None)
        if search_tool:
            print("\n=== Testing 'search' tool ===")
            args = {"query": "bitcoin price", "searchType": "web"}
            
            print(f"Calling search with args: {json.dumps(args)}")
            try:
                result = await session.call_tool("search", args)
                print(f"\nSearch result: {result.content}")
                return True
            except Exception as e:
                print(f"Error calling search tool: {e}")
                return False
        else:
            print("\n❌ 'search' tool not found in available tools")
            return False
            
    except Exception as e:
        print(f"❌ Error testing MCP: {e}")
        return False
    finally:
        await exit_stack.aclose()
        print("\n=== MCP Server Connection Closed ===")

if __name__ == "__main__":
    success = asyncio.run(test_local_mcp())
    if success:
        print("\n✅ Local MCP test completed successfully!")
    else:
        print("\n❌ Local MCP test failed. Please check the errors above.")