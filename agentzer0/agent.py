import os
import subprocess
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
import groq
import asyncio

# Minimal logging configuration
import logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger('AgentZer0')

load_dotenv()
GROQ_API = os.getenv("GROQ_API_KEY")
ANKR_API = os.getenv("ANKR_API_KEY")

# Validate Groq API key
if not GROQ_API:
    logger.error("GROQ_API_KEY is not set")
    raise ValueError("GROQ_API_KEY is required")

# Initialize Groq client and validate model
groq_client = groq.Groq(api_key=GROQ_API)
MODEL_NAME = "llama3-70b-8192"
try:
    groq_client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": "test"}],
        max_tokens=10
    )
except Exception as e:
    logger.error("Failed to validate Groq model: %s", e)
    raise

# Initialize LLM
llm = ChatGroq(
    model=MODEL_NAME,
    temperature=0.5,
    max_tokens=512,
    groq_api_key=GROQ_API
)

class AgentZer0:
    def __init__(self):
        # MCP server configuration
        mcp_config = {
            "web3-research-mcp": {
                "command": "node",
                "args": ["C:/Users/Sturgis/root.s/#SteeleBlockchainTechnology/Projects/GridZer0/AgentZer0_Discord/MCP_Servers/build/index.js"],
                "env": {"ANKR_API_KEY": ANKR_API} if ANKR_API else {},
                "transport": "stdio"
            }
        }

        # Start MCP server and initialize client
        try:
            self.server_process = subprocess.Popen(
                [mcp_config["web3-research-mcp"]["command"]] + mcp_config["web3-research-mcp"]["args"],
                env={**os.environ, **mcp_config["web3-research-mcp"]["env"]},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.mcp_client = MultiServerMCPClient(mcp_config)
            asyncio.run(asyncio.sleep(10))  # Wait for server startup
            mcp_tools = self.mcp_client.get_tools()
            tool_names = [tool.name for tool in mcp_tools]
            if not mcp_tools:
                logger.error("No tools loaded from MCP server")
        except Exception as e:
            logger.error("Failed to initialize MCP server: %s", e)
            raise

        # Initialize LangChain agent
        try:
            prompt = PromptTemplate.from_template(
                """
                You are a trading assistant for the GridZer0 trading community.
                A user has sent: "{query}".
                Available tools: {tool_names}
                Tools details: {tools}
                Use the following scratchpad: {agent_scratchpad}
                For crypto queries (e.g., price, market cap, wallet balance), use web3-research-mcp tools: token_price, wallet_balance, chain_data.
                If no tools are available, return: 'No web3-research-mcp tools available.'
                Provide a concise response.
                """
            )
            agent = create_react_agent(llm=llm, tools=mcp_tools, prompt=prompt)
            self.agent_executor = AgentExecutor(agent=agent, tools=mcp_tools, max_iterations=30)
        except Exception as e:
            logger.error("Failed to initialize agent: %s", e)
            raise

    def __del__(self):
        if hasattr(self, 'server_process') and self.server_process.poll() is None:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()

    async def process_message(self, message):
        text = message.content
        mcp_tools = self.mcp_client.get_tools()
        tool_names = [tool.name for tool in mcp_tools]
        if not any(tool in ['token_price', 'wallet_balance', 'chain_data'] for tool in tool_names):
            return {"should_respond": True, "response": "No web3-research-mcp tools available."}

        try:
            async with asyncio.timeout(30):
                response = await self.agent_executor.ainvoke({"query": text})
                return {"should_respond": True, "response": response.get("output", "No response generated")}
        except asyncio.TimeoutError:
            return {"should_respond": True, "response": "Web3 server timed out."}
        except Exception as e:
            return {"should_respond": True, "response": f"Error: {str(e)}"}