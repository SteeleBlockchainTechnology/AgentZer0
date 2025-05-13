# AgentZer0 Discord Integration

This folder contains the Discord bot integration for the AgentZer0 project. The Discord bot allows users to interact with the MCP client through Discord channels and direct messages.

## Structure

- `bot.py`: Main Discord bot implementation that connects to Discord API
- `commands.py`: Command handlers for Discord commands (e.g., !help, !tools)
- `events.py`: Event handlers for Discord events (e.g., messages, reactions)

## Setup

1. Create a Discord bot on the [Discord Developer Portal](https://discord.com/developers/applications)
2. Get your bot token from the Bot section
3. Add the token to your `.env` file:
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   ```
4. Invite the bot to your server using the OAuth2 URL generator in the Discord Developer Portal
   - Required permissions: Send Messages, Read Message History, Use Slash Commands
   - Required scopes: bot, applications.commands

## Usage

The Discord bot will automatically start when you run the main application if the `DISCORD_TOKEN` environment variable is set.

### Interacting with the Bot

- **Direct Messages**: Send a message directly to the bot
- **Mentions**: Mention the bot in a channel with your query: `@AgentZer0 what is the weather?`

### Commands

- `!help`: Display help information
- `!tools`: List available MCP tools

## Integration with MCP Client

The Discord bot uses the same MCP client as the API, allowing it to access the same tools and LLM capabilities. When a user sends a message to the bot, it:

1. Processes the message through the MCP client
2. Calls the LLM with the user's query
3. Executes any tool calls requested by the LLM
4. Returns the final response to the Discord user

## Troubleshooting

- If the bot doesn't start, check that your `DISCORD_TOKEN` is correctly set in the `.env` file
- If the bot starts but doesn't respond, check that it has the necessary permissions in your Discord server
- Check the application logs for any errors related to the Discord bot
