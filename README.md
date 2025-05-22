# AgentZer0 Discord Bot

A Discord bot that integrates with cryptocurrency price data and research tools, powered by Groq and OpenRouter LLMs.

## Overview

AgentZer0 is a Discord bot that can:

- Retrieve real-time cryptocurrency prices
- Research cryptocurrency tokens
- Answer questions about blockchain projects
- Process natural language queries using LLM technology

## Features

- **Real-time Cryptocurrency Data**: Access current prices, market summaries, and historical data
- **Token Research**: Research cryptocurrency projects using multiple data sources
- **Multi-LLM Support**: Primary Groq LLM with OpenRouter deepseek-chat as backup
- **Function Calling**: Automatically selects appropriate tools based on user queries
- **Conversation Memory**: Maintains context across messages

## Environment Variables

### Required

- `DISCORD_TOKEN`: Your Discord bot token
- `GROQ_API_KEY`: API key for the Groq LLM service

### Optional

- `GROQ_MODEL`: Specify a Groq model (default: "llama-3-8b-8192")
- `OPEN_ROUTER_API_KEY`: API key for OpenRouter (backup LLM)
- `OPEN_ROUTER_MODEL`: Specify an OpenRouter model (default: "deepseek/deepseek-chat-v3-0324:free")

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install poetry
   poetry install
   ```
3. Create a `.env` file with your environment variables:

   ```bash
   # Discord Bot Token
   DISCORD_TOKEN=your_discord_bot_token_here

   # Primary LLM - Groq
   GROQ_API_KEY=your_groq_api_key_here
   GROQ_MODEL=llama-3-8b-8192

   # Backup LLM - OpenRouter
   OPEN_ROUTER_API_KEY=your_openrouter_api_key_here
   OPEN_ROUTER_MODEL=deepseek/deepseek-chat-v3-0324:free
   ```

4. Run the bot:
   ```bash
   poetry run python main.py
   ```

## Usage

- To interact with the bot in Discord, @mention it by name
- Example: "@AgentZer0 What is the price of Bitcoin?"
- The bot will only respond to messages where it's explicitly mentioned
- Commands starting with ! don't need a mention (e.g., "!help")

## Architecture

- **Discord Bot**: Handles Discord API integration
- **MCP Client**: Manages connections to MCP servers and tools
- **Language Model**: Processes queries using Groq and OpenRouter LLMs
- **Tools**: Various tools for cryptocurrency data and research

## License

MIT
