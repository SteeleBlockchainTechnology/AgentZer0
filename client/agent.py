"""Agent module for handling LLM interactions and agentic workflows."""
import os
import logging
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from mcp_use.adapters.langchain_adapter import LangChainAdapter
from .mcp_client import MCPClientManager

logger = logging.getLogger(__name__)

class GroqAgent:
    """Manages Groq LLM interactions and agentic workflows with MCP tools."""
    
    def __init__(self, mcp_client_manager: MCPClientManager):

        self.mcp_client_manager = mcp_client_manager
        self.llm = None
        self.executor = None
        self.tools = []
        self._initialize_llm()
    
    def _initialize_llm(self):
    
        if not os.getenv("GROQ_API_KEY"):
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.llm = ChatOpenAI(
            model=os.getenv("GROQ_MODEL"),
            openai_api_key=os.getenv("GROQ_API_KEY"),
            openai_api_base=os.getenv("GROQ_BASE_URL"),
            temperature=0.3
        )
        logger.info("Groq LLM initialized successfully")
    
    async def setup_tools(self):
        
        try:
            async with await self.mcp_client_manager.get_managed_client() as client:
                adapter = LangChainAdapter()
                self.tools = await adapter.create_tools(client)
                tool_names = [tool.name for tool in self.tools]
                logger.info(f"Tools initialized: {tool_names}")
                
                # Create system prompt with available tools
                tool_names_str = ', '.join(tool_names)
                system_prompt = (
                    f"You are a helpful assistant with access to realtime data tools: {tool_names_str}. "
                    "You are able to answer questions about the data and provide insights based on the data. "
                    "You are also able to answer questions about the market and the crypto space in general by using your realtime data tools. "
                    "After calling a tool and receiving the result, provide a clear, helpful response to the user based on that result. "
                )
                
                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("human", "{input}"),
                    ("placeholder", "{agent_scratchpad}")
                ])
                
                # Create agent and executor
                agent = create_tool_calling_agent(self.llm, self.tools, prompt)
                self.executor = AgentExecutor(
                    agent=agent,
                    tools=self.tools,
                    max_iterations=10,
                    verbose=True,
                    return_intermediate_steps=True,
                    early_stopping_method="generate",
                    handle_parsing_errors=True
                )
                
                logger.info("Agent executor setup completed")
                
        except Exception as e:
            logger.error(f"Failed to setup tools: {e}")
            raise
    
    async def process_query(self, query: str, context: str = None) -> Dict[str, Any]:
        """Process a user query and return the agent's response."""
        
        if not self.executor:
            await self.setup_tools()
        
        try:
            # Add context to query if provided
            full_input = query
            if context:
                full_input = f"Context: {context}\n\nUser query: {query}"
            
            # Create a new MCP client connection for this query
            async with await self.mcp_client_manager.get_managed_client() as client:
                # Update tools with fresh MCP client connection
                adapter = LangChainAdapter()
                updated_tools = await adapter.create_tools(client)
                
                # Update executor with fresh tools
                self.executor.tools = updated_tools
                
                # Process the query
                result = await self.executor.ainvoke({
                    "input": full_input
                })
            
            logger.debug(f"Query processed: {query}")
            logger.debug(f"Intermediate steps: {result.get('intermediate_steps', [])}")
            
            return {
                'success': True,
                'response': result['output'],
                'intermediate_steps': result.get('intermediate_steps', []),
                'query': query
            }
            
        except Exception as e:
            logger.error(f"Error processing query '{query}': {e}")
            return {
                'success': False,
                'response': f"Sorry, I encountered an error while processing your request: {str(e)}",
                'error': str(e),
                'query': query
            }
    
    async def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        if not self.tools:
            await self.setup_tools()
        return [tool.name for tool in self.tools]
