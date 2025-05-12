"""
Tests for the LLM module.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from discord_mcp_bot.llm.groq_client import GroqClient
from discord_mcp_bot.mcp.client import MCPClient

@pytest.fixture
def groq_client():
    """Fixture for creating a Groq client."""
    with patch('groq.Client'):
        client = GroqClient("test_api_key", "test_model")
        return client

@pytest.fixture
def mcp_client():
    """Fixture for creating an MCP client with tools."""
    client = MagicMock(spec=MCPClient)
    client.get_available_tools.return_value = [
        {
            "type": "function",
            "function": {
                "name": "test_server.test_tool",
                "description": "A test tool",
                "parameters": {}
            }
        }
    ]
    client.execute_tool = AsyncMock(return_value={"result": "tool_result"})
    return client

class TestGroqClient:
    """Tests for the GroqClient class."""
    
    def test_init(self, groq_client):
        """Test initialization of the Groq client."""
        assert groq_client.api_key == "test_api_key"
        assert groq_client.model == "test_model"
    
    @pytest.mark.asyncio
    @patch('discord_mcp_bot.llm.groq_client.GroqClient._call_groq_api')
    async def test_process_message_no_tools(self, mock_call_api, groq_client):
        """Test processing a message without tools."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_call_api.return_value = mock_response
        
        # Test data
        user_message = "Hello"
        conversation_history = [
            {"role": "user", "content": "Hello"}
        ]
        
        # Call method
        response = await groq_client.process_message(user_message, conversation_history)
        
        # Verify
        assert response == "Test response"
        mock_call_api.assert_called_once()
        assert len(mock_call_api.call_args[0][0]) == 2  # System message + user message
    
    @pytest.mark.asyncio
    @patch('discord_mcp_bot.llm.groq_client.GroqClient._call_groq_api')
    async def test_process_message_with_tools(self, mock_call_api, groq_client, mcp_client):
        """Test processing a message with tools."""
        # Mock first API response with tool calls
        first_response = MagicMock()
        first_response.choices = [MagicMock()]
        first_response.choices[0].message.content = "I'll check that for you."
        
        # Add tool_calls attribute to the response
        tool_call = MagicMock()
        tool_call.id = "test_id"
        tool_call.function.name = "test_server.test_tool"
        tool_call.function.arguments = '{"param": "value"}'
        first_response.choices[0].message.tool_calls = [tool_call]
        
        # Mock second API response after tool execution
        second_response = MagicMock()
        second_response.choices = [MagicMock()]
        second_response.choices[0].message.content = "Based on the tool result, here's my answer."
        
        # Set up mock to return different responses
        mock_call_api.side_effect = [first_response, second_response]
        
        # Test data
        user_message = "Use a tool"
        conversation_history = [
            {"role": "user", "content": "Use a tool"}
        ]
        
        # Call method
        response = await groq_client.process_message(
            user_message, 
            conversation_history,
            context=None,
            mcp_client=mcp_client
        )
        
        # Verify
        assert response == "Based on the tool result, here's my answer."
        assert mock_call_api.call_count == 2
        
        # Verify tool execution
        mcp_client.execute_tool.assert_called_once_with(
            "test_server", 
            "test_tool", 
            {"param": "value"}
        )
        
        # Verify second API call includes tool results
        second_call_args = mock_call_api.call_args_list[1][0][0]
        assert len(second_call_args) == 4  # System + user + assistant (tool call) + tool
        assert second_call_args[2]["role"] == "assistant"
        assert second_call_args[2]["content"] is None
        assert second_call_args[2]["tool_calls"][0]["id"] == "test_id"
        assert second_call_args[3]["role"] == "tool"
        assert second_call_args[3]["tool_call_id"] == "test_id"