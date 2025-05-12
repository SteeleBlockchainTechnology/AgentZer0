# Discord Bot Integration for AgentZer0

This module integrates a Discord bot with the AgentZer0 application, allowing users to interact with the MCP client through Discord.

## Setup

1. Create a Discord bot through the [Discord Developer Portal](https://discord.com/developers/applications)
2. Add the bot to your server with appropriate permissions (read messages, send messages, etc.)
3. Set the following environment variables in your `.env` file:

```
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_PREFIX=!  # Optional, defaults to ! if not specified
```

## Usage

The bot will automatically start when the main application runs, as long as the `DISCORD_TOKEN` environment variable is set.

### Commands

The bot responds to messages in the following ways:

- Messages starting with the command prefix (default: `!`) will be processed as commands
- All other messages will be processed through the MCPClient and responded to accordingly

## Architecture

The Discord bot integration consists of three main components:

1. `bot.py` - Contains the `DiscordBot` class that handles Discord connectivity
2. `events.py` - Contains the `MessageHandler` class that processes messages through the MCPClient
3. Integration in `main.py` - Connects the Discord bot to the FastAPI application

The bot runs in a separate thread to avoid blocking the FastAPI application.
