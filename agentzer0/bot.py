# AgentZer0/bot.py
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
from agentzer0.agent import AgentZer0

# Configure logging
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
logger = logging.getLogger('AgentZer0Bot')

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

logger.info(f"Loaded DISCORD_TOKEN: {'Set' if TOKEN else 'Not Set'}")

# Set up intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

logger.info("Creating AgentZer0Agent instance")
agent = AgentZer0()

@bot.event
async def on_ready():
    logger.info(f"Bot logged in successfully as {bot.user}")
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        logger.debug("Ignoring message from bot itself")
        return
    
    logger.info(f"Received message from {message.author}: {message.content}")
    result = await agent.process_message(message)
    
    if result["should_respond"]:
        logger.info(f"Sending response: {result['response']}")
        await message.channel.send(result['response'])
    else:
        logger.info("No response needed for this message")
    
    await bot.process_commands(message)

@bot.command()
async def ping(ctx):
    logger.info(f"Ping command received from {ctx.author}")
    await ctx.send("Pong!")

if __name__ == "__main__":
    logger.info("Starting bot")
    bot.run(TOKEN)