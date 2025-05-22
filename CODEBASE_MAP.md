# AgentZer0 Codebase Map

This document provides a comprehensive breakdown of the AgentZer0 codebase, explaining how the various components interact.

## Architecture Overview

AgentZer0 is a Discord bot that integrates with cryptocurrency price data and research tools, powered by Groq and OpenRouter LLMs.

### Core Components:

1. **Discord Bot**: The user-facing interface that handles Discord interactions
2. **MCP Client**: Central component that manages connections to tool servers
3. **Language Model**: Interfaces with Groq/OpenRouter to provide LLM capabilities
4. **MCP Servers**: Various tool servers providing domain-specific functionality
5. **API Layer**: REST API exposing functionality for external consumption

```
                     +----------------+
                     |  Discord Bot   |
                     +-------+--------+
                             |
                     +-------v--------+
                     |  MCP Client    |<--------------+
                     +-------+--------+               |
                             |                        |
        +---------+----------+-----------+            |
        |         |          |           |            |
+-------v---+ +---v-----+ +--v------+ +--v--------+   |
|  LLM API  | |  Crypto | |  Web3   | |  Other    |   |
|(Groq/OR)  | |  Tools  | | Research| |  Servers  |   |
+-----------+ +---------+ +--+------+ +-----------+   |
                            |                         |
                     +------v-------+                 |
                     |  FastAPI     |-----------------|
                     +--------------+
```

## Directory Structure

### Top-Level Organization

- `client/`: Core client components for LLM and MCP servers
- `discord_bot/`: Discord interface and event handling
- `api/`: FastAPI implementation for REST endpoints
- `config/`: Configuration settings
- `mcp_servers/`: Tool servers for crypto data and research
- `utils/`: Utility functions
- `models/`: Data models/schemas
- `research_data/`: Storage for research outputs
- `main.py`: Application entry point

## Component Interactions

### 1. Application Initialization (`main.py`)

The application starts in `main.py`, which:

1. Creates a FastAPI application
2. Initializes the MCPClient
3. Connects to configured MCP servers
4. Creates the Discord bot (if token available)
5. Launches everything

```python
# Simplified flow
app = FastAPI()
client = MCPClient()
await client.initialize_servers()
discord_bot = DiscordBot(client)
await discord_bot.start(token)
```

### 2. Discord Bot Components

#### `discord_bot/bot.py`

- Implements `DiscordBot` class
- Initializes Discord connection
- Sets up command and event handlers
- Manages the bot lifecycle

#### `discord_bot/events.py`

- Implements `EventHandler` class
- Processes Discord events (messages, reactions)
- Handles @mentions
- Manages message processing workflow
- Extracts queries from messages
- Routes queries to MCPClient
- Processes function calls in responses
- Returns results to Discord users

#### `discord_bot/commands.py`

- Defines bot commands (prefixed with "!")
- Sets up command handlers
- Implements utility functions

### 3. Client Components

#### `client/mcp_client.py`

- Core orchestration component
- Manages connections to MCP servers
- Fetches available tools
- Routes function calls to appropriate servers
- Manages LLM interactions
- Processes queries end-to-end
- Handles tool execution results
- Manages conversation state

#### `client/language_model.py`

- Interfaces with LLM providers
- Implements primary (Groq) and backup (OpenRouter) LLMs
- Formats messages and tools for LLM
- Processes LLM responses
- Handles extraction of function calls
- Manages system prompts

#### `client/conversation.py`

- Manages conversation state
- Tracks message history
- Formats conversations for LLM context

### 4. MCP Server Components

#### `mcp_servers/crypto-market-data/`

- Implements crypto price and market data tools
- Tools include: get-price, get-market-summary, etc.
- Fetches real-time cryptocurrency data

#### `mcp_servers/web3-research-mcp/`

- Implements blockchain research tools
- Provides tools for token research
- Enables web search for crypto information

### 5. API Components

#### `api/routes.py`

- Defines REST API endpoints
- Exposes functionality for external consumption
- Routes API requests to MCPClient

### 6. Configuration

#### `config/settings.py`

- Loads environment variables
- Defines application configuration
- Specifies MCP server settings

### 7. Utilities and Models

#### `utils/logger.py`

- Configures application logging
- Provides logging functions

#### `models/schemas.py`

- Defines data models
- Specifies API schemas

## Data Flow Diagrams

### 1. Discord Message Processing Flow

```
User Message -> Discord API -> DiscordBot -> EventHandler -> MCPClient
    -> LLM -> MCP Tools -> Process Results -> Format Response -> Discord Reply
```

### 2. Function Call Execution Flow

```
LLM Response -> Extract Function Calls -> Find Appropriate Server
    -> Call Tool -> Format Result -> Replace in Response -> Return to User
```

### 3. Tool Server Initialization

```
MCPClient.initialize_servers -> Connect to Each Server -> Fetch Available Tools
    -> Format Tools for LLM -> Store Tool Mappings
```

## Key File Relationships

### Discord Bot Initialization Chain

```
main.py -> discord_bot/bot.py -> discord_bot/events.py + discord_bot/commands.py
```

### Query Processing Chain

```
discord_bot/events.py -> client/mcp_client.py -> client/language_model.py -> MCP Servers
```

### Configuration Loading Chain

```
main.py -> config/settings.py -> Environment Variables
```

## Component Interactions (Detailed)

### 1. Discord Message Processing

When a user sends a message mentioning the bot:

1. `discord_bot/events.py` receives the message
2. Message content is extracted and the bot mention is removed
3. A new MCPClient instance is created specifically for this query
4. The MCPClient connects to all configured tool servers
5. The query is sent to the LLM via language_model.py
6. The LLM generates a response, potentially with function calls
7. If function calls are present, they are executed against the appropriate tool servers
8. Results are formatted and sent back to the user
9. The MCPClient instance is cleaned up

### 2. Tool Execution Flow

When the LLM generates a function call:

1. `mcp_client.py` detects the function call pattern
2. The tool name is extracted and matched to a server
3. Arguments are parsed and validated
4. The tool is called on the appropriate server
5. Results are received and formatted
6. The function call text is replaced with the actual result
7. The final response is returned

### 3. LLM Failover Mechanism

When calling the LLM:

1. `language_model.py` first attempts to use Groq
2. If Groq fails (rate limit, etc.), it falls back to OpenRouter
3. The same interface is used for both providers
4. Tool calls from either provider are handled identically

## Advanced Features

### Multi-Provider LLM Support

- Primary provider: Groq
- Backup provider: OpenRouter with deepseek-chat
- Automatic failover when rate limits are hit

### Function Call Processing

- Multiple pattern recognition for different function call formats
- Robust error handling for failed tool calls
- Direct replacement of function calls with results

### Conversation Tracking

- Message history is maintained for context
- Tool calls and results are tracked
- Logging of all interactions for debugging

## Summary

The AgentZer0 codebase follows a modular architecture with clear separation of concerns:

1. **Discord Interface**: Handles user interactions
2. **MCP Client**: Provides core orchestration
3. **LLM Integration**: Enables AI capabilities
4. **Tool Servers**: Deliver domain-specific functionality
5. **API Layer**: Exposes services externally

The system's design allows for:

- Easy addition of new tool servers
- Flexible LLM provider switching
- Robust error handling
- Scalable processing of queries

This architecture enables the bot to provide real-time cryptocurrency data and research while maintaining a conversational interface.
