# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
# This file configures the application logging system.
# It sets up a standardized logger that is used throughout the application
# for consistent log formatting and output handling.

import logging  # Python's built-in logging module
import sys      # For stdout access

# Configure the root logger with consistent formatting and multiple outputs
logging.basicConfig(
    level=logging.INFO,  # Set default log level to INFO
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Timestamp, logger name, level, message
    handlers=[
        logging.StreamHandler(sys.stdout),  # Output logs to console
        logging.FileHandler("app.log"),     # Also save logs to app.log file
    ],
)

# Create a named logger for the application
# This logger is imported and used by other modules, particularly:
# - client/mcp_client.py: For logging client operations, tool calls, and errors
logger = logging.getLogger("mcp_client")