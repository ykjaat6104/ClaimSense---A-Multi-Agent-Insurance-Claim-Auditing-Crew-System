"""
Web search integration module supporting multiple search providers.
Provides unified interface for searching market prices, vendor verification, etc.
"""

import logging
from typing import Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Unified search result format."""
    title: str
    url: str
    snippet: str
    source: str = "web"


class TavilySearchClient:
    """Tavily search API integration."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.available = api_key is not None
    
    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Search using Tavily API."""
        if not self.available:
            logger.warning("Tavily API key not configured")
            return []
        
        try:
            from tavily import TavilyClient
            
            client = TavilyClient(api_key=self.api_key)
            response = client.search(query, max_results=max_results)
            
            results = []
            for result in response.get("results", []):
                results.append(SearchResult(
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                    snippet=result.get("content", ""),
                    source="tavily"
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            return []


class DuckDuckGoSearchClient:
    """DuckDuckGo search integration (free, no API key required)."""
    
    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Search using DuckDuckGo."""
        try:
            from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=max_results)
            
            search_results = []
            for result in results:
                search_results.append(SearchResult(
                    title=result.get("title", ""),
                    url=result.get("href", ""),
                    snippet=result.get("body", ""),
                    source="duckduckgo"
                ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []


class WebSearchService:
    """Unified web search service with fallback support."""
    
    def __init__(self, tavily_api_key: Optional[str] = None):
        self.tavily = TavilySearchClient(tavily_api_key)
        self.duckduckgo = DuckDuckGoSearchClient()
    
    def search_market_price(self, item_name: str, category: str = "") -> dict[str, Any]:
        """
        Search for fair market price of an item.
        
        Returns:
            {
                "item_name": str,
                "category": str,
                "results": list[SearchResult],
                "average_price": float (estimated from results),
                "price_range": {"min": float, "max": float},
                "data_quality": "HIGH" | "MEDIUM" | "LOW",
            }
        """
        query = f"{item_name} price {category}".strip()
        
        # Try Tavily first, fall back to DuckDuckGo
        results = []
        if self.tavily.available:
            results = self.tavily.search(query, max_results=5)
        
        if not results:
            results = self.duckduckgo.search(query, max_results=5)
        
        # Extract price information from results (simple regex-based extraction)
        prices = _extract_prices_from_results(results)
        
        return {
            "item_name": item_name,
            "category": category,
            "results": [
                {
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                    "source": r.source,
                }
                for r in results
            ],
            "average_price": sum(prices) / len(prices) if prices else 0.0,
            "price_range": {
                "min": min(prices) if prices else 0.0,
                "max": max(prices) if prices else 0.0,
            },
            "data_quality": "HIGH" if len(prices) > 2 else "MEDIUM" if prices else "LOW",
        }
    
    def search_repair_rates(self, repair_type: str, location: str = "") -> dict[str, Any]:
        """Search for regional repair rates."""
        query = f"{repair_type} repair cost {location}".strip()
        
        results = []
        if self.tavily.available:
            results = self.tavily.search(query, max_results=5)
        
        if not results:
            results = self.duckduckgo.search(query, max_results=5)
        
        prices = _extract_prices_from_results(results)
        
        return {
            "repair_type": repair_type,
            "location": location,
            "results": [
                {
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                    "source": r.source,
                }
                for r in results
            ],
            "average_cost": sum(prices) / len(prices) if prices else 0.0,
            "cost_range": {
                "min": min(prices) if prices else 0.0,
                "max": max(prices) if prices else 0.0,
            },
            "data_quality": "HIGH" if len(prices) > 2 else "MEDIUM" if prices else "LOW",
        }
    
    def verify_vendor(self, vendor_name: str, location: str = "") -> dict[str, Any]:
        """Verify vendor legitimacy and reputation."""
        query = f"{vendor_name} business license complaints {location}".strip()
        
        results = []
        if self.tavily.available:
            results = self.tavily.search(query, max_results=5)
        
        if not results:
            results = self.duckduckgo.search(query, max_results=5)
        
        # Simple sentiment analysis from snippets
        red_flags = []
        for result in results:
            snippet = result.snippet.lower()
            if any(keyword in snippet for keyword in ["complaint", "fraud", "scam", "lawsuit"]):
                red_flags.append(result.snippet[:100] + "...")
        
        return {
            "vendor_name": vendor_name,
            "location": location,
            "results": [
                {
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                    "source": r.source,
                }
                for r in results
            ],
            "is_legitimate": len(red_flags) == 0,
            "red_flags": red_flags,
            "data_quality": "MEDIUM" if results else "LOW",
        }


def _extract_prices_from_results(results: list[SearchResult]) -> list[float]:
    """Extract price values from search result snippets."""
    import re
    
    prices = []
    price_pattern = r'\$[\d,]+(?:\.\d{2})?|\b[\d,]+(?:\.\d{2})?\s*(?:dollars?|USD|usd)\b'
    
    for result in results:
        matches = re.findall(price_pattern, result.snippet)
        for match in matches:
            try:
                # Clean up the match
                clean = match.replace("$", "").replace(",", "").strip()
                price = float(clean.split()[0])  # Get first number if multiple
                if 0 < price < 1000000:  # Reasonable price range
                    prices.append(price)
            except (ValueError, IndexError):
                continue
    
    return prices


# Singleton instance
_web_search_service: Optional[WebSearchService] = None


def get_web_search_service(tavily_api_key: Optional[str] = None) -> WebSearchService:
    """Get or create the web search service singleton."""
    global _web_search_service
    if _web_search_service is None:
        _web_search_service = WebSearchService(tavily_api_key)
    return _web_search_service
