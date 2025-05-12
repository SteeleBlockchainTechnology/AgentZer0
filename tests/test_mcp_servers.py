"""Tests for the MCP servers module."""
import pytest
import os
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from discord_mcp_bot.mcp_servers.web3_research_server import Web3ResearchMCPServer

@pytest.fixture
def web3_research_server():
    """Fixture for creating a Web3 Research MCP server."""
    with patch('os.makedirs'), patch('os.path.join', return_value='mock_path'):
        server = Web3ResearchMCPServer()
        return server

class TestWeb3ResearchMCPServer:
    """Tests for the Web3ResearchMCPServer class."""
    
    def test_init(self, web3_research_server):
        """Test initialization of the Web3 Research MCP server."""
        assert hasattr(web3_research_server, 'resources_dir')
        assert hasattr(web3_research_server, 'research_dir')
        assert web3_research_server.current_research == {}
        assert web3_research_server.resources == {}
    
    def test_get_tools(self, web3_research_server):
        """Test getting tools from the Web3 Research MCP server."""
        tools = web3_research_server.get_tools()
        
        # Just check we have the expected number of tools
        assert len(tools) == 8
        
        # Check specific tool names
        tool_names = [tool["name"] for tool in tools]
        expected_tools = [
            "create_research_plan",
            "search_web",
            "search_token_with_keywords",
            "update_research_status",
            "fetch_url_content",
            "list_resources",
            "search_token_source",
            "start_comprehensive_research"
        ]
        for tool in expected_tools:
            assert tool in tool_names
    
    @pytest.mark.asyncio
    @patch('json.dump')
    @patch('builtins.open')
    async def test_execute_tool_create_research_plan(self, mock_open, mock_json_dump, web3_research_server):
        """Test executing the create_research_plan tool."""
        # Parameters for the tool
        parameters = {
            "token_name": "Bitcoin",
            "token_ticker": "BTC"
        }
        
        # Execute tool
        result = await web3_research_server.execute_tool("create_research_plan", parameters)
        
        # Verify
        assert result["success"] is True
        assert "Bitcoin" in result["message"]
        assert "BTC" in result["message"]
        assert "research_plan" in result
        
        # Verify research plan structure
        plan = result["research_plan"]
        assert plan["token_name"] == "Bitcoin"
        assert plan["token_ticker"] == "BTC"
        assert "sections" in plan
        assert len(plan["sections"]) == 8  # Should have 8 sections
    
    @pytest.mark.asyncio
    async def test_execute_tool_search_web(self, web3_research_server):
        """Test executing the search_web tool."""
        # Parameters for the tool
        parameters = {
            "query": "Bitcoin price",
            "search_type": "web"
        }
        
        # Execute tool and expect an exception
        with pytest.raises(Exception) as excinfo:
            await web3_research_server.execute_tool("search_web", parameters)
        
        # Verify the exception message
        assert "Search API connection not configured" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_execute_tool_invalid(self, web3_research_server):
        """Test executing an invalid tool."""
        with pytest.raises(Exception) as excinfo:
            await web3_research_server.execute_tool("nonexistent_tool", {})
        
        assert "Unknown tool" in str(excinfo.value)
        
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_execute_tool_fetch_url_content_success(self, mock_get, web3_research_server):
        """Test executing the fetch_url_content tool with a successful response."""
        # Mock the response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="Test content")
        mock_get.return_value.__aenter__.return_value = mock_response
        
        with patch('builtins.open', mock_open()), patch('json.dump'):
            # Parameters for the tool
            parameters = {
                "url": "https://example.com",
                "format": "text"
            }
            
            # Execute tool
            result = await web3_research_server.execute_tool("fetch_url_content", parameters)
            
            # Verify
            assert result["success"] is True
            assert result["url"] == "https://example.com"
            assert result["format"] == "text"
            assert "content_preview" in result
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_execute_tool_fetch_url_content_error(self, mock_get, web3_research_server):
        """Test executing the fetch_url_content tool with an error response."""
        # Mock the response with an error status
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Parameters for the tool
        parameters = {
            "url": "https://example.com/nonexistent",
            "format": "text"
        }
        
        # Execute tool and expect an exception
        with pytest.raises(Exception) as excinfo:
            await web3_research_server.execute_tool("fetch_url_content", parameters)
        
        # Verify the exception message
        assert "Failed to fetch URL: HTTP 404" in str(excinfo.value)
        
    @pytest.mark.asyncio
    async def test_execute_tool_search_token_with_keywords(self, web3_research_server):
        """Test executing the search_token_with_keywords tool."""
        # Parameters for the tool
        parameters = {
            "token_name": "Bitcoin",
            "token_ticker": "BTC",
            "keywords": ["whitepaper", "technology"]
        }
        
        # Execute tool and expect an exception
        with pytest.raises(Exception) as excinfo:
            await web3_research_server.execute_tool("search_token_with_keywords", parameters)
        
        # Verify the exception message
        assert "Keyword search API connection not configured" in str(excinfo.value)
        
    @pytest.mark.asyncio
    async def test_execute_tool_search_token_source(self, web3_research_server):
        """Test executing the search_token_source tool."""
        # Parameters for the tool
        parameters = {
            "token_name": "Bitcoin",
            "token_ticker": "BTC",
            "source": "CoinGecko"
        }
        
        # Execute tool and expect an exception
        with pytest.raises(Exception) as excinfo:
            await web3_research_server.execute_tool("search_token_source", parameters)
        
        # Verify the exception message
        assert "Source API connection to CoinGecko not configured" in str(excinfo.value)
        
    @pytest.mark.asyncio
    async def test_execute_tool_start_comprehensive_research(self, web3_research_server):
        """Test executing the start_comprehensive_research tool."""
        # Create a research plan first to avoid errors
        with patch('json.dump'), patch('builtins.open'):
            await web3_research_server._create_research_plan({
                "token_name": "Bitcoin",
                "token_ticker": "BTC"
            })
        
        # Parameters for the tool
        parameters = {
            "token_name": "Bitcoin",
            "token_ticker": "BTC"
        }
        
        # Execute tool and expect an exception
        with pytest.raises(Exception) as excinfo:
            await web3_research_server.execute_tool("start_comprehensive_research", parameters)
        
        # Verify the exception message
        assert "Comprehensive research APIs not configured" in str(excinfo.value)