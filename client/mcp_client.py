import logging
from contextlib import asynccontextmanager
from mcp_use.client import MCPClient
import mcp_use

logger = logging.getLogger(__name__)

class MCPClientManager:
    
    def __init__(self, config_file_path: str, debug_level: int = 2):
       
        self.config_file_path = config_file_path
        self.client = None
        # Enable mcp-use debug mode
        mcp_use.set_debug(debug_level)
    
    @asynccontextmanager
    async def manage_client(self, client):
        """Context manager for MCP client sessions.
        
        This will properly clean up sessions when the context is exited.
        """
        try:
            yield client
        finally:
            # Only disconnect sessions if explicitly requested
            # We don't automatically disconnect here to allow for reuse
            pass
    
    async def initialize(self):
        """Initialize the MCP client if not already initialized."""
        try:
            if not self.client:
                self.client = MCPClient.from_config_file(self.config_file_path)
                logger.info(f"MCP client initialized with config: {self.config_file_path}")
            return self.client
        except Exception as e:
            logger.error(f"Failed to initialize MCP client: {e}")
            raise
    
    async def get_managed_client(self):
        """Get a managed client instance."""
        if not self.client:
            await self.initialize()
        return self.manage_client(self.client)
    
    async def cleanup(self):
        """Clean up MCP client connections."""
        if self.client:
            for session in self.client.sessions.values():
                await session.disconnect()
            self.client.sessions.clear()
            logger.info("MCP client cleanup completed")
