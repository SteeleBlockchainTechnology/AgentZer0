# ============================================================================
# MAIN APPLICATION - CONFIGURED FOR WEB3 RESEARCH MCP
# ============================================================================
# This version is specifically designed to work with web3-research-mcp

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import os
import traceback

# Import application components
from client.mcp_client import MCPClient    # Client for MCP server communication
from config.settings import settings       # Application settings
from api.routes import router              # API route definitions
from discord_bot.bot import DiscordBot     # Discord bot integration


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    client = MCPClient()
    discord_bot = None
    discord_task = None
    
    try:
        print("\n===== STARTING AGENTZER0 WITH WEB3-RESEARCH-MCP =====")
        print(f"Node.js required: Make sure Node.js v16+ is installed")
        print(f"GROQ_API_KEY set: {'Yes' if os.environ.get('GROQ_API_KEY') else 'No'}")
        print(f"DISCORD_TOKEN set: {'Yes' if os.environ.get('DISCORD_TOKEN') else 'No'}")
        print("==================================================\n")
        
        # Connect to the web3-research-mcp server using npx
        print("Connecting to web3-research-mcp server...")
        try:
            # Call connect_to_server without parameters to use settings from config
            connected = await client.connect_to_server()
            if not connected:
                print("Failed to connect to web3-research-mcp server")
                raise HTTPException(
                    status_code=500, detail="Failed to connect to MCP server"
                )
            print("Successfully connected to web3-research-mcp server!")
        except Exception as e:
            print(f"Error connecting to MCP server: {e}")
            traceback.print_exc()
            raise
            
        # Store client in app state for dependency injection in routes
        app.state.client = client
        
        # Initialize Discord bot if token is available
        discord_token = os.environ.get("DISCORD_TOKEN")
        if discord_token:
            print("Initializing Discord bot...")
            try:
                # Create Discord bot
                discord_bot = DiscordBot(client)
                app.state.discord_bot = discord_bot
                
                # Start Discord bot in a separate task
                print("Starting Discord bot...")
                discord_task = asyncio.create_task(discord_bot.start(discord_token))
                
                # Note: We'll let the bot start in the background and continue with FastAPI startup
                print("Discord bot starting in background...")
            except Exception as e:
                print(f"Error initializing Discord bot: {e}")
                traceback.print_exc()
                # Don't raise here - we'll continue even if Discord fails
                print("Continuing startup without Discord bot")
        else:
            print("DISCORD_TOKEN not found. Discord bot not started.")
            
        print("Application initialization complete!")
        yield
        print("Application shutdown initiated...")
    except Exception as e:
        print(f"Error during lifespan: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error during lifespan") from e
    finally:
        # Ensure client is properly cleaned up on application shutdown
        print("Cleaning up resources...")
        if client:
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
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title="AgentZer0 Web3 Research API", 
        lifespan=lifespan,
        description="API for crypto research with web3-research-mcp tools"
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
    
    print("Starting AgentZer0 Web3 Research application...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")