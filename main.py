from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
from contextlib import asynccontextmanager
from mcp_client import MCPClient
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
import os
import asyncio
import threading
from discord_bot import DiscordBot
from discord_bot.events import MessageHandler

load_dotenv()


class Settings(BaseSettings):
    server_script_path: str = "npx"
    server_script_args: list[str] = ["-y", "web3-research-mcp@latest"]
    discord_token: str = os.getenv("DISCORD_TOKEN", "")
    discord_prefix: str = os.getenv("DISCORD_PREFIX", "!")


settings = Settings()


# Discord bot instance
discord_bot = None
discord_thread = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global discord_bot, discord_thread
    client = MCPClient()
    try:
        # Connect to MCP server
        connected = await client.connect_to_server(settings.server_script_path, settings.server_script_args)
        if not connected:
            raise HTTPException(
                status_code=500, detail="Failed to connect to MCP server"
            )
        app.state.client = client
        
        # Initialize Discord bot if token is available
        if settings.discord_token:
            discord_bot = DiscordBot(settings.discord_token, settings.discord_prefix)
            
            # Set up message handler
            message_handler = MessageHandler(client)
            discord_bot.add_message_handler(message_handler.handle_message)
            
            # Set up bot events
            await discord_bot.setup_events()
            
            # Start Discord bot in a separate thread
            discord_thread = threading.Thread(target=discord_bot.run)
            discord_thread.daemon = True
            discord_thread.start()
        else:
            print("Discord token not found. Discord bot will not be started.")
        
        yield
    except Exception as e:
        print(f"Error during lifespan: {e}")
        raise HTTPException(status_code=500, detail="Error during lifespan") from e
    finally:
        # shutdown
        await client.cleanup()


app = FastAPI(title="MCP Client API", lifespan=lifespan)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


class QueryRequest(BaseModel):
    query: str


class Message(BaseModel):
    role: str
    content: Any


class ToolCall(BaseModel):
    name: str
    args: Dict[str, Any]


@app.post("/query")
async def process_query(request: QueryRequest):
    """Process a query and return the response"""
    try:
        messages = await app.state.client.process_query(request.query)
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools")
async def get_tools():
    """Get the list of available tools"""
    try:
        tools = await app.state.client.get_mcp_tools()
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                }
                for tool in tools
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)