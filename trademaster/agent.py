# trademaster/agent.py
import os
import sys
import logging
from dotenv import load_dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from praisonaiagents.tools import get_stock_price, get_stock_info, get_historical_data
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
import groq  # Add this line

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TradeMasterAgent')

load_dotenv()
GROQ_API = os.getenv("GROQ_API_KEY")
llm = ChatGroq(
    model="groq/llama3-70b-8192",
    temperature=0.5,
    max_tokens=512,
    client = groq.Groq(api_key=GROQ_API)
)

class TradeMasterAgent:
    def __init__(self):
        logger.info("Initializing TradeMasterAgent")
        
        # Define CrewAI agent
        self.agent = Agent(
            role="Trading Assistant",
            goal="Provide concise, trading-related answers to messages using the tools provided to you",
            backstory="You are GridZer0 AI, a knowledgeable AI assistant for the GridZer0 trading community, skilled in fetching stock prices, company info, and historical data.",
            verbose=True,
            llm= llm
        )
        logger.info("TradeMasterAgent initialized successfully")

    async def process_message(self, message):
        logger.info(f"Processing message: {message.content}")
        text = message.content

        try:
            # Define task for the agent
            task = Task(
                description=f"""
                Respond to the following Discord message with a concise, trading-related answer: "{text}"
                Use the stock tools (get_stock_price, get_stock_info, get_historical_data) if the message involves stock queries.
                Maintain a natural conversation flow.
                """,
                agent=self.agent,
                expected_output="A concise, trading-related response to the user's message."
            )

            # Create and run a Crew with the agent and task
            crew = Crew(
                agents=[self.agent],
                tasks=[task],
                verbose=True
            )
            response = crew.kickoff()
            
            logger.info(f"Response generated: {response}")
            return {"should_respond": True, "response": str(response)}
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {"should_respond": True, "response": "I'm having trouble processing your request. Please try again later."}