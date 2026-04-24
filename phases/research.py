"""Phase 1: Research & Discovery engine."""
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from clients.openrouter import OpenRouterClient
from clients.tavily import TavilyClient
from clients.scraper import WebScraper
from models.research import ResearchResult, BusinessProfile, BuyerPersona, BrandVoice, Competitor, ResearchEvidence
from utils.prompts import RESEARCH_SYSTEM_PROMPT, RESEARCH_USER_PROMPT
from utils.logger import logger
from config.settings import settings

class ResearchEngine:
    """Enterprise-grade research engine for business intelligence."""
    
    def __init__(
        self,
        llm: Optional[OpenRouterClient] = None,
        search: Optional[TavilyClient] = None,
        scraper: Optional[WebScraper] = None
    ):
        self.llm = llm or OpenRouterClient()
        self.search = search or TavilyClient()
        self.scraper = scraper or WebScraper()
        logger.info("ResearchEngine initialized")
    
    async def run(self, business_url: str) -> ResearchResult:
        """
        Execute full research pipeline.
        
        1. Scrape website and discover pages
        2. Run targeted searches
        3. Synthesize with LLM
        4. Validate and structure output
        """
        logger.info(f"🔍 Starting research for: {business_url}")
        
        # Step 1: Scrape website
        scraped_pages = await self._scrape_website(business_url)
        
        # Step 2: Search for additional intelligence
        search_results = await self._search_intelligence(business_url, scraped_pages)
        
        # Step 3: Synthesize with LLM
        research_data = await self._synthesize_research(
            business_url, scraped_pages, search_results
        )
        
        # Step 4: Parse and validate
        result = self._parse_research_result(research_data, business_url, scraped_pages, search_results)
        
        logger.info(
            f"✅ Research complete | business={result.business.name} | "
            f"confidence={result.confidence_score:.2f} | "
            f"personas={len(result.audience)} | competitors={len(result.competitors)}"
        )
        
        return result
    
    async def _scrape_website(self, url: str) -> List[Dict[str, Any]]:
        """Scrape website and discover key pages."""
        logger.info(f"🌐 Scraping website: {url}")
        try:
            pages = await self.scraper.discover_pages(url, max_pages=10)
            logger.info(f"📄 Scraped {len(pages)} pages")
            return pages
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            # Fallback: at least try homepage
            try:
                homepage = await self.scraper.scrape(url)
                return [homepage]
            except Exception as e2:
                logger.error(f"Homepage scraping also failed: {e2}")
                return [{"url": url, "text": "", "title": "", "links": []}]
    
    async def _search_intelligence(
        self,
        url: str,
        scraped_pages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Run targeted searches for additional intelligence."""
        # Extract business name from first page
        business_name = scraped_pages[0].get("title", "").split("-")[0].strip() if scraped_pages else ""
        
        queries = [
            f"{business_name} company review",
            f"{business_name} competitors",
            f"{business_name} target audience customers",
        ]
        
        # Add domain-specific query
        domain = url.replace("https://", "").replace("http://", "").split("/")[0]
        queries.append(f"site:{domain} about")
        
        logger.info(f"🔎 Running {len(queries)} search queries")
        
        try:
            results = await self.search.multi_search(queries)
            valid_results = []
            for r in results:
                if isinstance(r, Exception):
                    logger.warning(f"Search query failed: {r}")
                else:
                    valid_results.append(r)
            logger.info(f"📊 Got {len(valid_results)} search results")
            return valid_results
        except Exception as e:
            logger.error(f"Search intelligence failed: {e}")
            return []
    
    async def _synthesize_research(
        self,
        url: str,
        scraped_pages: List[Dict[str, Any]],
        search_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use LLM to synthesize all research data."""
        
        # Prepare scraped content
        scraped_content = "\n\n".join([
            f"--- PAGE: {p.get('url', '')} ---\n"
            f"TITLE: {p.get('title', '')}\n"
            f"META: {p.get('meta_description', '')}\n"
            f"CONTENT:\n{p.get('text', '')[:3000]}"
            for p in scraped_pages[:5]  # Limit to avoid token overflow
        ])
        
        # Prepare search results
        search_content = "\n\n".join([
            f"--- SEARCH RESULTS ---\n"
            + "\n".join([
                f"- {r.get('title', '')}: {r.get('content', r.get('snippet', ''))[:500]}"
                for r in result.get("results", [])[:5]
            ])
            + f"\nAI ANSWER: {result.get('answer', '')}"
            for result in search_results[:3]
        ])
        
        user_prompt = RESEARCH_USER_PROMPT.format(
            url=url,
            scraped_content=scraped_content[:8000],
            search_results=search_content[:4000]
        )
        
        logger.info("🧠 Synthesizing research with LLM...")
        
        try:
            result = await self.llm.generate_json(
                system_prompt=RESEARCH_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=4000
            )
            return result
        except Exception as e:
            logger.error(f"LLM synthesis failed: {e}")
            # Return minimal structure
            return {
                "business": {
                    "name": "Unknown",
                    "description": "Could not extract business information",
                    "industry": "Unknown",
                    "niche": "Unknown",
                    "products": [],
                    "value_proposition": "Unknown"
                },
                "audience": [],
                "brand_voice": {
                    "tone": "Professional",
                    "style": "Clear and concise",
                    "keywords": [],
                    "avoid": [],
                    "examples": []
                },
                "competitors": [],
                "content_examples": [],
                "evidence": {"source_urls": [url], "quotes": [], "search_queries_used": []},
                "confidence_score": 0.1,
                "summary": "Research failed. Using minimal fallback data."
            }
    
    def _parse_research_result(
        self,
        data: Dict[str, Any],
        url: str,
        scraped_pages: List[Dict[str, Any]],
        search_results: List[Dict[str, Any]]
    ) -> ResearchResult:
        """Parse LLM output into structured ResearchResult."""
        
        business_data = data.get("business", {})
        business = BusinessProfile(
            name=business_data.get("name", "Unknown"),
            tagline=business_data.get("tagline"),
            description=business_data.get("description", ""),
            industry=business_data.get("industry", "Unknown"),
            niche=business_data.get("niche", "Unknown"),
            products=business_data.get("products", []),
            value_proposition=business_data.get("value_proposition", ""),
            target_market=business_data.get("target_market", ""),
            founded=business_data.get("founded"),
            size=business_data.get("size")
        )
        
        audience = [
            BuyerPersona(**p) for p in data.get("audience", [])
        ]
        
        brand_data = data.get("brand_voice", {})
        brand_voice = BrandVoice(
            tone=brand_data.get("tone", "Professional"),
            style=brand_data.get("style", "Clear"),
            keywords=brand_data.get("keywords", []),
            avoid=brand_data.get("avoid", []),
            examples=brand_data.get("examples", [])
        )
        
        competitors = [
            Competitor(**c) for c in data.get("competitors", [])
        ]
        
        evidence_data = data.get("evidence", {})
        evidence = ResearchEvidence(
            source_urls=evidence_data.get("source_urls", [url]),
            quotes=evidence_data.get("quotes", []),
            search_queries_used=evidence_data.get("search_queries_used", [])
        )
        
        return ResearchResult(
            business=business,
            audience=audience,
            brand_voice=brand_voice,
            competitors=competitors,
            content_examples=data.get("content_examples", []),
            evidence=evidence,
            raw_data={
                "scraped_pages": len(scraped_pages),
                "search_results": len(search_results),
                "timestamp": datetime.utcnow().isoformat()
            },
            confidence_score=data.get("confidence_score", 0.5),
            summary=data.get("summary", "")
        )
