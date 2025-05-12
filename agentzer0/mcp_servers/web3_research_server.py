"""
Web3 Research MCP server implementation.
This server provides tools for conducting deep research on cryptocurrency tokens.
Based on the functionality of the web3-research-mcp Node.js package by aaronjmars.
"""
import logging
import asyncio
import aiohttp
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class Web3ResearchMCPServer:
    """MCP server for cryptocurrency research."""
    
    def __init__(self):
        """Initialize the Web3 Research MCP server."""
        self.resources_dir = os.path.join(os.getcwd(), "resources")
        self.research_dir = os.path.join(os.getcwd(), "research")
        
        # Create directories if they don't exist
        os.makedirs(self.resources_dir, exist_ok=True)
        os.makedirs(self.research_dir, exist_ok=True)
        
        # Store current research state
        self.current_research = {}
        self.resources = {}
    
    def get_tools(self):
        """Get all tools this server provides.
        
        Returns:
            list: List of tool definitions.
        """
        return [
            {
                "name": "create_research_plan",
                "description": "Creates a structured research plan for a cryptocurrency token",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "token_name": {
                            "type": "string",
                            "description": "Full name of the token (e.g., 'Bitcoin')"
                        },
                        "token_ticker": {
                            "type": "string",
                            "description": "Ticker symbol of the token (e.g., 'BTC')"
                        }
                    },
                    "required": ["token_name", "token_ticker"]
                }
            },
            {
                "name": "search_web",
                "description": "Performs a web search and returns the results",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "search_type": {
                            "type": "string",
                            "description": "Type of search (web, news, images, videos)",
                            "enum": ["web", "news", "images", "videos"],
                            "default": "web"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "search_token_with_keywords",
                "description": "Searches for a token with specific keywords and saves the results",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "token_name": {
                            "type": "string",
                            "description": "Name of the token"
                        },
                        "token_ticker": {
                            "type": "string",
                            "description": "Ticker symbol of the token"
                        },
                        "keywords": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "Array of keywords to search for"
                        }
                    },
                    "required": ["token_name", "token_ticker", "keywords"]
                }
            },
            {
                "name": "update_research_status",
                "description": "Updates the status of a research section",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "section": {
                            "type": "string",
                            "description": "Section name to update (e.g., 'project_info', 'technical_fundamentals')"
                        },
                        "status": {
                            "type": "string",
                            "description": "New status for the section",
                            "enum": ["planned", "in_progress", "completed"]
                        }
                    },
                    "required": ["section", "status"]
                }
            },
            {
                "name": "fetch_url_content",
                "description": "Fetches content from a URL and saves it as a resource",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to fetch content from"
                        },
                        "format": {
                            "type": "string",
                            "description": "Output format",
                            "enum": ["text", "html", "markdown", "json"],
                            "default": "text"
                        }
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "list_resources",
                "description": "Lists all available resources that have been saved",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "search_token_source",
                "description": "Searches for information about a token from a specific source",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "token_name": {
                            "type": "string",
                            "description": "Name of the token"
                        },
                        "token_ticker": {
                            "type": "string",
                            "description": "Ticker symbol of the token"
                        },
                        "source": {
                            "type": "string",
                            "description": "Source to search (e.g., 'CoinGecko', 'DeFiLlama', 'News')",
                            "enum": ["CoinGecko", "CoinMarketCap", "DeFiLlama", "News", "Twitter", "GitHub", "Reddit"]
                        }
                    },
                    "required": ["token_name", "token_ticker", "source"]
                }
            },
            {
                "name": "start_comprehensive_research",
                "description": "Initiates comprehensive research on a cryptocurrency token",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "token_name": {
                            "type": "string",
                            "description": "Full name of the cryptocurrency token"
                        },
                        "token_ticker": {
                            "type": "string",
                            "description": "Ticker symbol of the token (e.g., BTC, ETH)"
                        }
                    },
                    "required": ["token_name", "token_ticker"]
                }
            }
        ]
    
    async def execute_tool(self, tool_name, parameters):
        """Execute a specific tool with the given parameters.
        
        Args:
            tool_name (str): Name of the tool to execute.
            parameters (dict): Parameters for the tool.
            
        Returns:
            dict: Result of the tool execution.
            
        Raises:
            Exception: If the tool execution fails or if the API connections are not configured.
        """
        # Log the tool execution attempt
        logger.info(f"Executing Web3 Research tool: {tool_name}")
        
        # We're removing the try/except block to allow exceptions to propagate
        # This ensures the LLM gets accurate error information when APIs aren't available
        if tool_name == "create_research_plan":
            return await self._create_research_plan(parameters)
        elif tool_name == "search_web":
            return await self._search_web(parameters)
        elif tool_name == "search_token_with_keywords":
            return await self._search_token_with_keywords(parameters)
        elif tool_name == "update_research_status":
            return await self._update_research_status(parameters)
        elif tool_name == "fetch_url_content":
            return await self._fetch_url_content(parameters)
        elif tool_name == "list_resources":
            return await self._list_resources()
        elif tool_name == "search_token_source":
            return await self._search_token_source(parameters)
        elif tool_name == "start_comprehensive_research":
            return await self._start_comprehensive_research(parameters)
        else:
            raise Exception(f"Unknown tool: {tool_name}")
    
    async def _create_research_plan(self, parameters):
        """Create a structured research plan for a token.
        
        Args:
            parameters (dict): Parameters including token_name and token_ticker.
            
        Returns:
            dict: Research plan structure.
        """
        token_name = parameters["token_name"]
        token_ticker = parameters["token_ticker"]
        
        logger.info(f"Creating research plan for {token_name} ({token_ticker})")
        
        # Create a research plan structure
        research_plan = {
            "token_name": token_name,
            "token_ticker": token_ticker,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "sections": {
                "project_info": {
                    "status": "planned",
                    "description": "Basic information about the project, team, and history"
                },
                "technical_fundamentals": {
                    "status": "planned",
                    "description": "Technical analysis of the token's blockchain, consensus mechanism, and features"
                },
                "tokenomics": {
                    "status": "planned",
                    "description": "Token distribution, supply, inflation, and economic model"
                },
                "market_data": {
                    "status": "planned",
                    "description": "Price history, market cap, volume, and liquidity"
                },
                "community_and_social": {
                    "status": "planned",
                    "description": "Social media presence, community size, and sentiment"
                },
                "development_activity": {
                    "status": "planned",
                    "description": "GitHub activity, development roadmap, and recent updates"
                },
                "competitors": {
                    "status": "planned",
                    "description": "Analysis of competing projects and market positioning"
                },
                "risks_and_concerns": {
                    "status": "planned",
                    "description": "Potential risks, security concerns, and regulatory issues"
                }
            },
            "resources": []
        }
        
        # Save the research plan
        research_id = f"{token_ticker.lower()}_research"
        research_file_path = os.path.join(self.research_dir, f"{research_id}.json")
        
        with open(research_file_path, 'w') as f:
            json.dump(research_plan, f, indent=2)
        
        # Update current research state
        self.current_research = research_plan
        
        return {
            "success": True,
            "message": f"Research plan created for {token_name} ({token_ticker})",
            "research_plan": research_plan
        }
    
    async def _search_web(self, parameters):
        """Perform a web search and return results.
        
        Args:
            parameters (dict): Parameters including query and search_type.
            
        Returns:
            dict: Search results.
            
        Raises:
            Exception: If the search API is unavailable or returns an error.
        """
        query = parameters["query"]
        search_type = parameters.get("search_type", "web")
        
        logger.info(f"Web search requested for query: {query}, type: {search_type}")
        
        # This is where you would implement the actual API call to a search service
        # For now, we'll raise an exception to indicate that the API is not implemented
        raise Exception("Search API connection not configured. Unable to perform web search.")
    
    async def _search_token_with_keywords(self, parameters):
        """Search for a token with specific keywords.
        
        Args:
            parameters (dict): Parameters including token_name, token_ticker, and keywords.
            
        Returns:
            dict: Search results.
            
        Raises:
            Exception: If the search API is unavailable or returns an error.
        """
        token_name = parameters["token_name"]
        token_ticker = parameters["token_ticker"]
        keywords = parameters["keywords"]
        
        logger.info(f"Searching for {token_name} ({token_ticker}) with {len(keywords)} keywords")
        
        # This method relies on the _search_web method which now raises an exception
        # The exception will propagate up from _search_web
        raise Exception(f"Keyword search API connection not configured. Unable to search for {token_name} with keywords.")
    
    async def _update_research_status(self, parameters):
        """Update the status of a research section.
        
        Args:
            parameters (dict): Parameters including section and status.
            
        Returns:
            dict: Updated research plan.
        """
        section = parameters["section"]
        status = parameters["status"]
        
        if not self.current_research:
            return {"error": "No active research plan. Create one first with create_research_plan."}
        
        if section not in self.current_research["sections"]:
            return {"error": f"Section '{section}' not found in research plan"}
        
        # Update the section status
        self.current_research["sections"][section]["status"] = status
        self.current_research["updated_at"] = datetime.now().isoformat()
        
        # Save updated research plan
        token_ticker = self.current_research["token_ticker"]
        research_id = f"{token_ticker.lower()}_research"
        research_file_path = os.path.join(self.research_dir, f"{research_id}.json")
        
        with open(research_file_path, 'w') as f:
            json.dump(self.current_research, f, indent=2)
        
        return {
            "success": True,
            "message": f"Status of section '{section}' updated to '{status}'",
            "research_plan": self.current_research
        }
    
    async def _fetch_url_content(self, parameters):
        """Fetch content from a URL and save as a resource.
        
        Args:
            parameters (dict): Parameters including url and format.
            
        Returns:
            dict: Fetched content and resource information.
            
        Raises:
            Exception: If the URL cannot be fetched or content cannot be processed.
        """
        url = parameters["url"]
        output_format = parameters.get("format", "text")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to fetch URL: HTTP {response.status}")
                    
                    content = await response.text()
                    
                    # Process content based on format
                    if output_format == "json":
                        try:
                            content = json.loads(content)
                            logger.info(f"Successfully parsed JSON content from {url}")
                        except json.JSONDecodeError:
                            raise Exception("Failed to parse content as JSON")
                    elif output_format in ["html", "markdown"]:
                        logger.info(f"Retrieved {output_format} content from {url}")
                    
                    # Save content as a resource
                    resource_id = f"url_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    resource_file_path = os.path.join(self.resources_dir, f"{resource_id}.{output_format}")
                    
                    if output_format == "json":
                        with open(resource_file_path, 'w') as f:
                            json.dump(content, f, indent=2)
                    else:
                        with open(resource_file_path, 'w') as f:
                            f.write(content)
                    
                    # Add to resources dictionary
                    self.resources[resource_id] = {
                        "type": "url_content",
                        "url": url,
                        "format": output_format,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # If there's active research, add this resource to it
                    if self.current_research:
                        self.current_research["resources"].append({
                            "id": resource_id,
                            "type": "url_content",
                            "url": url,
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        # Save updated research plan
                        token_ticker = self.current_research["token_ticker"]
                        research_id = f"{token_ticker.lower()}_research"
                        research_file_path = os.path.join(self.research_dir, f"{research_id}.json")
                        
                        with open(research_file_path, 'w') as f:
                            json.dump(self.current_research, f, indent=2)
                    
                    return {
                        "success": True,
                        "url": url,
                        "format": output_format,
                        "resource_id": resource_id,
                        "content_preview": str(content)[:500] + "..." if len(str(content)) > 500 else content
                    }
        except Exception as e:
            # Re-raise the exception with additional context
            raise Exception(f"Failed to fetch URL: {str(e)}")
    
    async def _list_resources(self):
        """List all available resources.
        
        Returns:
            dict: List of resources.
        """
        return {
            "success": True,
            "resources": self.resources
        }
    
    async def _search_token_source(self, parameters):
        """Search for token information from a specific source.
        
        Args:
            parameters (dict): Parameters including token_name, token_ticker, and source.
            
        Returns:
            dict: Search results.
            
        Raises:
            Exception: If the source API is unavailable or returns an error.
        """
        token_name = parameters["token_name"]
        token_ticker = parameters["token_ticker"]
        source = parameters["source"]
        
        logger.info(f"Token source search requested for {token_name} ({token_ticker}) from {source}")
        
        # In a real implementation, this would connect to the specific API for each source
        # For now, we'll raise an exception to indicate that the API is not implemented
        raise Exception(f"Source API connection to {source} not configured. Unable to search for {token_name} ({token_ticker}).")
    
    async def _start_comprehensive_research(self, parameters):
        """Start comprehensive research on a token.
        
        Args:
            parameters (dict): Parameters including token_name and token_ticker.
            
        Returns:
            dict: Research plan and initial results.
            
        Raises:
            Exception: If any of the required API connections fail.
        """
        token_name = parameters["token_name"]
        token_ticker = parameters["token_ticker"]
        
        logger.info(f"Starting comprehensive research for {token_name} ({token_ticker})")
        
        # Create a research plan - this is the only part that doesn't require external APIs
        research_plan = await self._create_research_plan({
            "token_name": token_name,
            "token_ticker": token_ticker
        })
        
        # For the actual research components that require API connections,
        # we'll raise an exception to indicate that the APIs are not implemented
        raise Exception(f"Comprehensive research APIs not configured. Unable to perform full research for {token_name} ({token_ticker}).")