"""Web scraping client using multiple strategies."""
import re
from typing import Optional, List, Dict, Any
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from tenacity import retry, stop_after_attempt, wait_exponential
from config.settings import settings
from utils.logger import logger

class ScrapingError(Exception):
    pass

class WebScraper:
    """Enterprise web scraper with multiple fallback strategies."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
            follow_redirects=True
        )
        self.firecrawl_api_key = settings.FIRECRAWL_API_KEY
        logger.info("Web scraper initialized")
    
    async def scrape(
        self,
        url: str,
        strategy: str = "auto",
        extract_text_only: bool = True
    ) -> Dict[str, Any]:
        """
        Scrape a URL with automatic fallback.
        
        Strategies: auto, firecrawl, http, playwright
        """
        url = self._normalize_url(url)
        
        if strategy == "auto":
            strategies = ["http", "firecrawl"]
        else:
            strategies = [strategy]
        
        last_error = None
        for strat in strategies:
            try:
                if strat == "http":
                    return await self._scrape_http(url, extract_text_only)
                elif strat == "firecrawl" and self.firecrawl_api_key:
                    return await self._scrape_firecrawl(url)
                elif strat == "playwright":
                    return await self._scrape_playwright(url)
            except Exception as e:
                last_error = e
                logger.warning(f"Scrape strategy '{strat}' failed for {url}: {e}")
                continue
        
        raise ScrapingError(f"All scraping strategies failed for {url}: {last_error}")
    
    async def _scrape_http(
        self,
        url: str,
        extract_text_only: bool = True
    ) -> Dict[str, Any]:
        """Basic HTTP scraping with BeautifulSoup."""
        response = await self.client.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()
        
        title = soup.find("title")
        title_text = title.get_text(strip=True) if title else ""
        
        # Extract meta description
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag:
            meta_desc = meta_tag.get("content", "")
        
        # Extract main content
        text = ""
        if extract_text_only:
            # Try to find main content area
            for selector in ["main", "article", "[role='main']", ".content", "#content", "body"]:
                elem = soup.select_one(selector)
                if elem:
                    text = elem.get_text(separator="\n", strip=True)
                    break
        
        # Extract links
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            absolute = urljoin(url, href)
            if self._is_same_domain(absolute, url):
                links.append({
                    "url": absolute,
                    "text": a.get_text(strip=True)[:100]
                })
        
        return {
            "url": url,
            "title": title_text,
            "meta_description": meta_desc,
            "text": text[:20000],  # Limit size
            "links": links[:50],
            "strategy": "http",
            "status_code": response.status_code
        }
    
    async def _scrape_firecrawl(self, url: str) -> Dict[str, Any]:
        """Scrape using Firecrawl API."""
        if not self.firecrawl_api_key:
            raise ScrapingError("Firecrawl API key not configured")
        
        fc_client = httpx.AsyncClient(timeout=60)
        try:
            response = await fc_client.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers={"Authorization": f"Bearer {self.firecrawl_api_key}"},
                json={"url": url, "onlyMainContent": True}
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                raise ScrapingError(f"Firecrawl failed: {data}")
            
            result = data.get("data", {})
            return {
                "url": url,
                "title": result.get("title", ""),
                "meta_description": result.get("description", ""),
                "text": result.get("markdown", result.get("content", ""))[:20000],
                "links": [{"url": l, "text": ""} for l in result.get("links", [])[:50]],
                "strategy": "firecrawl",
                "status_code": 200
            }
        finally:
            await fc_client.aclose()
    
    async def _scrape_playwright(self, url: str) -> Dict[str, Any]:
        """Scrape using Playwright for JS-rendered pages."""
        # This is a placeholder - in production you'd use actual Playwright
        # For now, we'll raise an error to fallback
        raise ScrapingError("Playwright scraping not implemented in this version")
    
    async def discover_pages(
        self,
        base_url: str,
        max_pages: int = 10
    ) -> List[Dict[str, Any]]:
        """Discover and scrape key pages from a website."""
        base_url = self._normalize_url(base_url)
        
        # First, scrape homepage to find links
        homepage = await self.scrape(base_url)
        pages = [homepage]
        
        # Priority pages to look for
        priority_patterns = [
            r"/about",
            r"/blog",
            r"/products",
            r"/services",
            r"/solutions",
            r"/pricing",
            r"/features",
            r"/company",
            r"/team",
            r"/contact"
        ]
        
        found_urls = set(p["url"] for p in pages)
        
        for link in homepage.get("links", []):
            link_url = link["url"]
            if link_url in found_urls:
                continue
            
            # Check if it's a priority page
            is_priority = any(
                re.search(pattern, link_url, re.IGNORECASE) 
                for pattern in priority_patterns
            )
            
            if is_priority and len(pages) < max_pages:
                try:
                    page_data = await self.scrape(link_url)
                    pages.append(page_data)
                    found_urls.add(link_url)
                except Exception as e:
                    logger.warning(f"Failed to scrape {link_url}: {e}")
        
        logger.info(f"Discovered {len(pages)} pages from {base_url}")
        return pages
    
    def _normalize_url(self, url: str) -> str:
        """Ensure URL has scheme."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url
    
    def _is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs are on the same domain."""
        try:
            return urlparse(url1).netloc == urlparse(url2).netloc
        except:
            return False
    
    async def close(self):
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
