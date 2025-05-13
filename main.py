# ============================================================================
# MAIN APPLICATION ENTRY POINT
# ============================================================================
# This file serves as the entry point for the AgentZer0 application.
# It initializes the FastAPI application, sets up the MCP client connection,
# configures middleware, and includes the API routes.

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import application components
from client.mcp_client import MCPClient  # Client for MCP server communication
from config.settings import settings      # Application settings
from api.routes import router             # API route definitions


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager
    
    This context manager handles the lifecycle of the MCP client:
    1. Initializes the MCP client and connects to the server on startup
    2. Stores the client in the app state for use by API routes
    3. Cleans up the client connection on shutdown
    
    Args:
        app: The FastAPI application instance
        
    Yields:
        None: Control is yielded back to FastAPI during application runtime
        
    Raises:
        HTTPException: If connection to the MCP server fails
    """
    client = MCPClient()
    try:
        # Connect to the MCP server using the path from settings
        connected = await client.connect_to_server(settings.server_script_path)
        if not connected:
            raise HTTPException(
                status_code=500, detail="Failed to connect to MCP server"
            )
        # Store client in app state for dependency injection in routes
        app.state.client = client
        yield
    except Exception as e:
        print(f"Error during lifespan: {e}")
        raise HTTPException(status_code=500, detail="Error during lifespan") from e
    finally:
        # Ensure client is properly cleaned up on application shutdown
        await client.cleanup()


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