"""
Test script for AgentZer0 components
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from client.mcp_client import MCPClientManager
from client.agent import GroqAgent

async def test_mcp_client():
    """Test MCP client initialization."""
    print("🔍 Testing MCP Client...")
    try:
        manager = MCPClientManager("config/mcp_servers.json")
        async with await manager.get_managed_client() as client:
            print("✅ MCP Client initialized successfully")
            return True
    except Exception as e:
        print(f"❌ MCP Client test failed: {e}")
        return False

async def test_agent():
    """Test Groq Agent initialization."""
    print("🔍 Testing Groq Agent...")
    try:
        manager = MCPClientManager("config/mcp_servers.json")
        agent = GroqAgent(manager)
        tools = await agent.get_available_tools()
        print(f"✅ Groq Agent initialized with tools: {tools}")
        
        # Test a simple query
        result = await agent.process_query("What tools do you have available?")
        print(f"✅ Test query result: {result['success']}")
        return True
    except Exception as e:
        print(f"❌ Groq Agent test failed: {e}")
        return False

async def main():
    """Run all tests."""
    load_dotenv()
    
    print("🚀 Running AgentZer0 Component Tests\n")
    
    # Check environment variables
    required_vars = ["GROQ_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please copy .env.example to .env and fill in your API keys")
        return
    
    tests = [
        test_mcp_client,
        test_agent
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your setup is ready.")
    else:
        print("⚠️  Some tests failed. Please check your configuration.")

if __name__ == "__main__":
    asyncio.run(main())
