"""Async SerpApi client for Google, Maps, and public OSINT discovery."""
import asyncio
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config.settings import settings
from utils.logger import logger


class SerpApiError(Exception):
    pass


class SerpApiClient:
    """Thin async wrapper around SerpApi's `/search.json` endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_results: Optional[int] = None,
        location: Optional[str] = None,
        gl: Optional[str] = None,
        hl: Optional[str] = None,
    ):
        self.api_key = api_key or settings.SERPAPI_KEY
        self.max_results = max_results or settings.SERPAPI_MAX_RESULTS
        self.location = location if location is not None else settings.SERPAPI_LOCATION
        self.gl = gl or settings.SERPAPI_GL
        self.hl = hl or settings.SERPAPI_HL
        self.base_url = "https://serpapi.com/search.json"
        self.client = httpx.AsyncClient(timeout=45)
        logger.info(f"SerpApi client initialized | max_results={self.max_results}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)),
    )
    async def search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run a SerpApi search and normalize API/metadata errors."""
        if not self.api_key:
            raise SerpApiError("SERPAPI_KEY is not configured")

        payload = {
            "api_key": self.api_key,
            "hl": self.hl,
            "gl": self.gl,
            **params,
        }
        try:
            response = await self.client.get(self.base_url, params=payload)
            response.raise_for_status()
            data = response.json()
            if data.get("error"):
                raise SerpApiError(str(data["error"]))
            status = data.get("search_metadata", {}).get("status")
            if status == "Error":
                raise SerpApiError(str(data.get("search_metadata", {})))
            return data
        except httpx.HTTPStatusError as e:
            logger.error(f"SerpApi HTTP error: {e.response.status_code} - {e.response.text}")
            raise SerpApiError(f"HTTP {e.response.status_code}: {e.response.text}")
        except SerpApiError:
            raise
        except Exception as e:
            logger.error(f"SerpApi error: {e}")
            raise SerpApiError(str(e))

    async def google_search(self, query: str, **kwargs) -> Dict[str, Any]:
        params = {
            "engine": "google",
            "q": query,
            "num": kwargs.pop("num", self.max_results),
            **kwargs,
        }
        if self.location and "location" not in params:
            params["location"] = self.location
        return await self.search(params)

    async def maps_search(self, query: str, **kwargs) -> Dict[str, Any]:
        params = {
            "engine": "google_maps",
            "q": query,
            "type": "search",
            **kwargs,
        }
        if self.location and "ll" not in params and "location" not in params:
            params["location"] = self.location
        return await self.search(params)

    async def multi_google_search(self, queries: List[str], **kwargs) -> List[Dict[str, Any]]:
        tasks = [self.google_search(query, **kwargs) for query in queries]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def local_intelligence(self, business_name: str, domain: str) -> Dict[str, Any]:
        """Collect Maps/local data and nearby competitor signals."""
        queries = [business_name, f"{business_name} {domain}"]
        results = []
        for query in queries:
            try:
                data = await self.maps_search(query)
                results.append({"query": query, "data": data})
            except Exception as e:
                logger.warning(f"SerpApi maps search failed for '{query}': {e}")
        return {"tool": "serpapi", "engine": "google_maps", "results": results}

    async def discover_social_profiles(self, business_name: str, domain: str) -> Dict[str, Any]:
        """Find public social/directory footprints through Google operators."""
        platforms = {
            "instagram": "instagram.com",
            "linkedin": "linkedin.com/company OR linkedin.com/in",
            "facebook": "facebook.com",
            "x": "twitter.com OR x.com",
            "youtube": "youtube.com",
            "tiktok": "tiktok.com",
            "google_maps": "google.com/maps",
            "reviews": "reviews OR rating OR testimonials",
        }
        queries = [
            f'"{business_name}" {operator}'
            for operator in platforms.values()
            if business_name
        ]
        queries.extend([
            f'"{domain}" instagram linkedin facebook reviews',
            f'"{business_name}" competitors alternatives' if business_name else f'"{domain}" competitors',
        ])
        raw_results = await self.multi_google_search(queries[:8])
        return {
            "tool": "serpapi",
            "engine": "google",
            "queries": queries[:8],
            "results": [r for r in raw_results if not isinstance(r, Exception)],
            "errors": [str(r) for r in raw_results if isinstance(r, Exception)],
        }

    def normalize_organic_results(self, result: Dict[str, Any], source_type: str = "search") -> List[Dict[str, Any]]:
        items = []
        for item in result.get("organic_results", [])[: self.max_results]:
            items.append({
                "tool": "serpapi",
                "source_type": source_type,
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", item.get("description", "")),
                "position": item.get("position"),
                "raw": item,
            })
        return items

    def normalize_maps_results(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        items = []
        for item in result.get("local_results", [])[: self.max_results]:
            items.append({
                "tool": "serpapi",
                "source_type": "google_maps",
                "title": item.get("title", ""),
                "url": item.get("website", item.get("link", "")),
                "snippet": item.get("description", ""),
                "rating": item.get("rating"),
                "reviews": item.get("reviews"),
                "address": item.get("address"),
                "phone": item.get("phone"),
                "category": item.get("type"),
                "gps_coordinates": item.get("gps_coordinates"),
                "place_id": item.get("place_id"),
                "raw": item,
            })
        return items

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
