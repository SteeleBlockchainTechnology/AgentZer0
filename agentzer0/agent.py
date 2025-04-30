# AgentZer0/agent.py
import os
import sys
import logging
from dotenv import load_dotenv
from crewai import Agent, Crew, Process, Task
from langchain_groq import ChatGroq
import groq

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('AgentZer0')

load_dotenv()
GROQ_API = os.getenv("GROQ_API_KEY")
llm = ChatGroq(
    model="groq/llama3-70b-8192",
    temperature=0.5,
    max_tokens=512,
    client = groq.Groq(api_key=GROQ_API)
)

class AgentZer0:
    def __init__(self):
        logger.info("Initializing AgentZer0")
        
        # Define CrewAI agent
        self.agent = Agent(
role="Trading Assistant",
            goal="Provide concise, trading-related answers to messages using the tools provided",
            backstory="You are AgentZer0, a knowledgeable AI assistant for the GridZer0 trading community, skilled in fetching stock prices, company info, and historical data. You can describe your capabilities when asked.",
            verbose=True,
            llm= llm
        )
        logger.info("AgentZer0 initialized successfully")

    async def process_message(self, message):
        logger.info(f"Processing message: {message.content}")
        text = message.content

        try:
            # Define task for the agent
            task = Task(
                description=f"""
                You are a trading assistant. A user has sent the following message: "{text}". 
                Provide a concise, trading-related response. 
                - If the message asks about specific stocks or data, use the available tools (get_stock_price, get_stock_info, get_historical_data) to fetch the information. 
                - If the message is general or about your capabilities, describe what you can do.
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