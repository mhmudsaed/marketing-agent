"""Tavily search client for AI-optimized web search."""
from typing import List, Dict, Any, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config.settings import settings
from utils.logger import logger

class TavilyError(Exception):
    pass

class TavilyClient:
    """Enterprise Tavily search client."""
    
    def __init__(self, api_key: Optional[str] = None, max_results: int = 10):
        self.api_key = api_key or settings.TAVILY_API_KEY
        self.max_results = max_results or settings.TAVILY_MAX_RESULTS
        self.base_url = "https://api.tavily.com"
        self.client = httpx.AsyncClient(timeout=30)
        logger.info(f"Tavily client initialized | max_results={self.max_results}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException))
    )
    async def search(
        self,
        query: str,
        search_depth: str = "advanced",
        include_answer: bool = True,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        max_results: Optional[int] = None
    ) -> Dict[str, Any]:
        """Perform AI-optimized web search."""
        
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": search_depth,
            "include_answer": include_answer,
            "max_results": max_results or self.max_results,
        }
        
        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains
        
        try:
            response = await self.client.post(
                f"{self.base_url}/search",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            logger.debug(
                f"Tavily search | query='{query[:50]}...' | "
                f"results={len(data.get('results', []))}"
            )
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Tavily HTTP error: {e.response.status_code} - {e.response.text}")
            raise TavilyError(f"HTTP {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Tavily error: {e}")
            raise TavilyError(str(e))
    
    async def multi_search(
        self,
        queries: List[str],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Run multiple searches concurrently."""
        import asyncio
        tasks = [self.search(q, **kwargs) for q in queries]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def close(self):
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
