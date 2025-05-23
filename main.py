import asyncio
import os
import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from mcp_use.client import MCPClient
from mcp_use.adapters.langchain_adapter import LangChainAdapter
from contextlib import asynccontextmanager
import mcp_use

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
load_dotenv()

# Enable mcp-use debug mode
mcp_use.set_debug(2)  # Full verbose output

@asynccontextmanager
async def manage_client(client):
    try:
        yield client
    finally:
        for session in client.sessions.values():
            await session.disconnect()
        client.sessions.clear()

async def main():
    # Verify API key
    if not os.getenv("GROQ_API_KEY"):
        raise ValueError("GROQ_API_KEY not found in .env")

    # Initialize MCP client
    async with manage_client(MCPClient.from_config_file("config/mcp_servers.json")) as client:
        llm = ChatOpenAI(
            model=os.getenv("GROQ_MODEL"),
            openai_api_key=os.getenv("GROQ_API_KEY"),
            openai_api_base=os.getenv("GROQ_BASE_URL"),
            temperature=0.3
        )
        
        # Create adapter and bind tools
        adapter = LangChainAdapter()
        tools = await adapter.create_tools(client)
        tool_names = [tool.name for tool in tools]
        logger.debug(f"Tools: {tool_names}")
        tool_names_str = ', '.join(tool_names)
        system_prompt = (
            f"You are a helpful assistant with access to cryptocurrency data tools: {tool_names_str}. "
            "When users ask for cryptocurrency prices or market data, use the appropriate tools to get current information. "
            "After calling a tool and receiving the result, provide a clear, helpful response to the user based on that result. "
            "Do not call the same tool multiple times unless the user asks for different information."
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
          # Create custom LangChain agent
        agent = create_tool_calling_agent(llm, tools, prompt)
        executor = AgentExecutor(
            agent=agent, 
            tools=tools, 
            max_iterations=10,  # Reduced to prevent infinite loops
            verbose=True, 
            return_intermediate_steps=True,
            early_stopping_method="generate",  # Generate response even if max iterations reached
            handle_parsing_errors=True
        )
        result = await executor.ainvoke({
            "input": "price of BTC"
        })
        logger.debug(f"Intermediate steps: {result['intermediate_steps']}")
        
        # Format and display the final response nicely
        print("\n" + "="*60)
        print("🤖 AGENT RESPONSE")
        print("="*60)
        print(f"📝 Query: price of BTC")
        print("-"*60)
        print(f"💬 Response:")
        print(f"   {result['output']}")
        print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())