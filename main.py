# ============================================================================
# MAIN APPLICATION ENTRY POINT
# ============================================================================
# This file serves as the entry point for the AgentZer0 application.
# It initializes the FastAPI application, sets up the MCP client connection,
# configures middleware, includes the API routes, and starts the Discord bot.

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import os

# Import application components
from client.mcp_client import MCPClient  # Client for MCP server communication
from config.settings import settings      # Application settings
from api.routes import router             # API route definitions
from discord_bot.bot import DiscordBot        # Discord bot integration


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager
    
    This context manager handles the lifecycle of the MCP client and Discord bot:
    1. Initializes the MCP client and connects to the server on startup
    2. Initializes the Discord bot and connects to Discord
    3. Stores the client in the app state for use by API routes
    4. Cleans up the client and bot connections on shutdown
    
    Args:
        app: The FastAPI application instance
        
    Yields:
        None: Control is yielded back to FastAPI during application runtime
        
    Raises:
        HTTPException: If connection to the MCP server fails
    """
    client = MCPClient()
    discord_bot = None
    discord_task = None
    
    try:
        # Connect to the MCP server using the path from settings
        connected = await client.connect_to_server(settings.server_script_path)
        if not connected:
            raise HTTPException(
                status_code=500, detail="Failed to connect to MCP server"
            )
            
        # Store client in app state for dependency injection in routes
        app.state.client = client
        
        # Initialize Discord bot if token is available
        discord_token = os.environ.get("DISCORD_TOKEN")
        if discord_token:
            # Create and initialize Discord bot
            discord_bot = DiscordBot(client)
            app.state.discord_bot = discord_bot
            
            # Start Discord bot in a separate task
            discord_task = asyncio.create_task(discord_bot.start(discord_token))
            print("Discord bot started")
        else:
            print("DISCORD_TOKEN not found. Discord bot not started.")
            
        yield
    except Exception as e:
        print(f"Error during lifespan: {e}")
        raise HTTPException(status_code=500, detail="Error during lifespan") from e
    finally:
        # Ensure client is properly cleaned up on application shutdown
        await client.cleanup()
        
        # Clean up Discord bot if it was started
        if discord_bot:
            await discord_bot.close()
            
        # Cancel Discord task if it was created
        if discord_task and not discord_task.done():
            discord_task.cancel()
            try:
                await discord_task
            except asyncio.CancelledError:
                pass


def create_application() -> FastAPI:
    """Create and configure the FastAPI application
    
    This function:
    1. Creates a new FastAPI instance with the lifespan manager
    2. Configures CORS middleware to allow cross-origin requests
    3. Includes the API routes from the router
    
    Returns:
        FastAPI: The configured FastAPI application
    """
    app = FastAPI(
        title="MCP Client API", 
        lifespan=lifespan,
        description="API for interacting with the MCP server and LLM"
    )
    
    # Add CORS middleware to allow cross-origin requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )
    
    # Include API routes defined in api/routes.py
    app.include_router(router)
    
    return app


# Create the FastAPI application instance
app = create_application()


# Run the application when executed directly
if __name__ == "__main__":
    import uvicorn

    # Start the uvicorn server
    uvicorn.run(app, host="0.0.0.0", port=8000)