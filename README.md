# AgentZer0 Discord Bot

A modular Discord bot that integrates Groq LLM with MCP (Model Context Protocol) clients to provide cryptocurrency data and other tools through Discord mentions.

## 🏗️ Project Structure

```
AgentZer0/
├── main.py                 # Entry point - orchestrates all components
├── test_components.py      # Test script for validating setup
├── .env.example           # Environment variables template
├── pyproject.toml         # Project dependencies
├── config/
│   └── mcp_servers.json   # MCP server configuration
├── client/                # MCP and LLM logic
│   ├── __init__.py
│   ├── mcp_client.py      # MCP client management
│   └── agent.py           # Groq LLM agent with tools
├── discord/               # Discord bot logic
│   ├── __init__.py
│   ├── bot.py             # Discord bot configuration
│   └── events.py          # Event handlers (mentions, responses)
└── mcp_servers/           # MCP server implementations
    └── mcp-server-ccxt/   # Cryptocurrency data server
```

## 🚀 Features

- **Discord Integration**: Responds to @mentions in Discord channels
- **Groq LLM**: Powered by Groq's fast inference with Llama models
- **MCP Protocol**: Extensible tool system for cryptocurrency data
- **Rate Limiting**: Prevents spam with configurable cooldowns
- **Context Awareness**: Uses recent message history for better responses
- **Modular Design**: Clean separation of concerns for easy maintenance
- **Error Handling**: Comprehensive error handling and logging
- **Graceful Shutdown**: Proper cleanup of connections and resources

## Architecture

The project consists of several key components:

- `main.py`: Main application entry point and agent orchestration
- `mcp_client.py`: MCP client implementation (currently empty, ready for custom extensions)
- `config/mcp_servers.json`: Configuration for MCP servers and tools
- `pyproject.toml`: Poetry project configuration and dependencies

## Dependencies

### Core Dependencies

- **mcp-use[search]**: Model Context Protocol client with search capabilities
- **langchain[openai]**: LangChain framework with OpenAI integration
- **python-dotenv**: Environment variable management
- **playwright**: Web automation (via MCP server)

### Python Version

- Requires Python 3.13+

## Installation

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd AgentZer0Final
   ```

2. **Install Poetry** (if not already installed):

   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Install dependencies**:

   ```bash
   poetry install
   ```

4. **Set up environment variables**:
   Create a `.env` file in the project root:

   ```env
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   ```

5. **Install Playwright** (for web automation):
   ```bash
   npx playwright install
   ```

## Configuration

### MCP Servers

The agent is configured to use Playwright for web automation. The configuration is stored in `config/mcp_servers.json`:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"],
      "env": {
        "DISPLAY": ":1"
      }
    }
  }
}
```

### Language Model

The agent is configured to use Mistral Small 3.1 24B via OpenRouter. You can modify the model in `main.py`:

```python
llm = ChatOpenAI(
    model="mistralai/mistral-small-3.1-24b-instruct:free",
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    openai_api_base="https://openrouter.ai/api/v1",
    temperature=0.7,
)
```

## Usage

### Running the Agent

```bash
poetry run python main.py
```

### Example Tasks

The current implementation demonstrates searching for Bitcoin prices:

```python
result = await agent.run(
    "search online for current price of btc.",
)
```

### Customizing Tasks

You can modify the task in `main.py` by changing the prompt passed to `agent.run()`:

```python
result = await agent.run(
    "Your custom task here",
)
```

## Development

### Project Structure

```
AgentZer0Final/
├── main.py                 # Main application entry point
├── mcp_client.py           # Custom MCP client (extensible)
├── pyproject.toml          # Poetry configuration
├── poetry.lock             # Dependency lock file
├── .env                    # Environment variables (create this)
├── .gitignore              # Git ignore rules
└── config/
    └── mcp_servers.json    # MCP server configurations
```

### Adding New Capabilities

1. **New MCP Servers**: Add server configurations to `config/mcp_servers.json`
2. **Custom Tools**: Implement custom functionality in `mcp_client.py`
3. **New Tasks**: Modify the agent prompts in `main.py`

### Agent Configuration

The agent is configured with:

- **Max Steps**: 30 (maximum reasoning/action steps)
- **Server Manager**: Enabled for automatic MCP server management
- **Temperature**: 0.7 (creativity vs consistency balance)

## Environment Variables

Required environment variables:

- `OPENROUTER_API_KEY`: Your OpenRouter API key for accessing language models
- `DISPLAY`: X11 display for Playwright (Linux/WSL environments)

## License

This project is part of the GridZer0/AgentZer0_Discord project suite.

## Author

- **Sturgis Steele** - sturgis.steele@outlook.com

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Troubleshooting

### Common Issues

1. **Missing API Key**: Ensure your `.env` file contains a valid `OPENROUTER_API_KEY`
2. **Playwright Issues**: Run `npx playwright install` to install browser dependencies
3. **Python Version**: Ensure you're using Python 3.13 or higher
4. **Display Issues**: Set `DISPLAY=:1` in your environment for headless operation

### Getting Help

For issues and questions:

- Check the error logs for specific error messages
- Ensure all dependencies are properly installed
- Verify your API key has sufficient credits
- Check that Playwright browsers are installed

## Future Enhancements

Potential areas for development:

- Discord bot integration
- Additional MCP server integrations
- Custom tool development
- Task scheduling and automation
- Result persistence and logging
