"""Phase 1: Research & Discovery engine."""
import asyncio
import json
import re
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional
from datetime import datetime
from clients.openrouter import OpenRouterClient
from clients.tavily import TavilyClient
from clients.scraper import WebScraper
from clients.serpapi import SerpApiClient
from models.research import (
    ResearchResult, BusinessProfile, BuyerPersona, BrandVoice, Competitor,
    ResearchEvidence, BusinessLocation, SocialProfile, ReviewsSummary,
    OSINTSource, SearchToolCoverage
)
from utils.prompts import RESEARCH_SYSTEM_PROMPT, RESEARCH_USER_PROMPT
from utils.logger import logger
from config.settings import settings

class ResearchEngine:
    """Enterprise-grade research engine for business intelligence."""
    
    def __init__(
        self,
        llm: Optional[OpenRouterClient] = None,
        search: Optional[TavilyClient] = None,
        scraper: Optional[WebScraper] = None,
        serpapi: Optional[SerpApiClient] = None
    ):
        self.llm = llm or OpenRouterClient()
        self.search = search or TavilyClient()
        self.scraper = scraper or WebScraper()
        self.serpapi = serpapi or SerpApiClient()
        logger.info("ResearchEngine initialized")
    
    async def run(self, business_url: str, extra_context: str = "") -> ResearchResult:
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
        search_results = await self._search_intelligence(business_url, scraped_pages, extra_context=extra_context)
        
        # Step 3: Synthesize with LLM
        research_data = await self._synthesize_research(
            business_url, scraped_pages, search_results, extra_context=extra_context
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
        scraped_pages: List[Dict[str, Any]],
        extra_context: str = ""
    ) -> List[Dict[str, Any]]:
        """Run deep OSINT searches across SerpApi, Tavily, and Firecrawl."""
        business_name = self._infer_business_name(url, scraped_pages)
        domain = urlparse(self.scraper._normalize_url(url)).netloc.replace("www.", "")
        queries = self._build_osint_queries(business_name, domain, extra_context=extra_context)

        logger.info(
            f"🔎 Running deep OSINT | business='{business_name}' | "
            f"tavily={len(queries['tavily'])} | serpapi={len(queries['serpapi'])}"
        )

        tavily_task = self._run_tavily_osint(queries["tavily"])
        serpapi_task = self._run_serpapi_osint(business_name, domain, queries["serpapi"])
        tavily_results, serpapi_bundle = await asyncio.gather(tavily_task, serpapi_task)

        osint_sources = self._normalize_osint_sources(scraped_pages, tavily_results, serpapi_bundle)
        firecrawl_pages = await self._firecrawl_discovered_sources(osint_sources)
        coverage = self._build_tool_coverage(scraped_pages, tavily_results, serpapi_bundle, firecrawl_pages, osint_sources)

        logger.info(
            f"📊 OSINT complete | sources={len(osint_sources)} | "
            f"maps={len(serpapi_bundle.get('maps_sources', []))} | "
            f"social={len(self._extract_social_profiles(osint_sources))}"
        )

        return [
            {
                "tool": "tavily",
                "queries": queries["tavily"],
                "results": tavily_results,
            },
            {
                "tool": "serpapi",
                "queries": queries["serpapi"],
                **serpapi_bundle,
            },
            {
                "tool": "firecrawl",
                "results": firecrawl_pages,
            },
            {
                "tool": "osint_normalized",
                "business_name_guess": business_name,
                "domain": domain,
                "sources": [s.model_dump() for s in osint_sources],
                "coverage": coverage.model_dump(),
                "social_profiles": [p.model_dump() for p in self._extract_social_profiles(osint_sources)],
                "locations": [l.model_dump() for l in self._extract_locations(serpapi_bundle)],
                "reviews_summary": self._extract_reviews_summary(serpapi_bundle, osint_sources).model_dump(),
                "competitor_evidence": [s.model_dump() for s in self._extract_competitor_evidence(osint_sources)],
            },
        ]
    
    def _infer_business_name(self, url: str, scraped_pages: List[Dict[str, Any]]) -> str:
        """Best-effort business name from title/domain before LLM synthesis."""
        title = scraped_pages[0].get("title", "") if scraped_pages else ""
        title = re.split(r"\s[-|–]\s", title)[0].strip()
        if title and len(title) > 2:
            return title[:80]
        domain = urlparse(self.scraper._normalize_url(url)).netloc.replace("www.", "")
        return domain.split(".")[0].replace("-", " ").title()
    
    def _build_osint_queries(self, business_name: str, domain: str, extra_context: str = "") -> Dict[str, List[str]]:
        brand = f'"{business_name}"' if business_name else f'"{domain}"'
        context_suffix = f" {extra_context[:160]}" if extra_context else ""
        tavily_queries = [
            f"{brand} business model target customers positioning{context_suffix}",
            f"{brand} reviews customer pain points testimonials{context_suffix}",
            f"{brand} competitors alternatives market",
            f"{brand} Instagram LinkedIn Facebook social media",
            f"site:{domain} about services pricing customers",
            f"{domain} brand voice content examples{context_suffix}",
        ]
        serpapi_queries = [
            f"{brand} official website",
            f"{brand} reviews ratings",
            f"{brand} competitors alternatives",
            f"{brand} Instagram",
            f"{brand} LinkedIn",
            f"{brand} Facebook",
            f"{brand} Google Maps",
            f"site:{domain} about services pricing contact",
        ]
        return {"tavily": tavily_queries, "serpapi": serpapi_queries}
    
    async def _run_tavily_osint(self, queries: List[str]) -> List[Dict[str, Any]]:
        try:
            results = await self.search.multi_search(
                queries,
                search_depth=settings.TAVILY_SEARCH_DEPTH,
                max_results=settings.TAVILY_MAX_RESULTS,
            )
            return [r for r in results if not isinstance(r, Exception)]
        except Exception as e:
            logger.error(f"Tavily OSINT failed: {e}")
            return []
    
    async def _run_serpapi_osint(self, business_name: str, domain: str, queries: List[str]) -> Dict[str, Any]:
        bundle: Dict[str, Any] = {
            "organic_results": [],
            "maps_results": [],
            "organic_sources": [],
            "maps_sources": [],
            "errors": [],
        }
        try:
            organic_results = await self.serpapi.multi_google_search(queries)
            for result in organic_results:
                if isinstance(result, Exception):
                    bundle["errors"].append(str(result))
                    continue
                bundle["organic_results"].append(result)
                bundle["organic_sources"].extend(self.serpapi.normalize_organic_results(result))
        except Exception as e:
            logger.warning(f"SerpApi Google OSINT failed: {e}")
            bundle["errors"].append(str(e))
        
        try:
            local = await self.serpapi.local_intelligence(business_name, domain)
            bundle["maps_results"] = local.get("results", [])
            for item in local.get("results", []):
                bundle["maps_sources"].extend(self.serpapi.normalize_maps_results(item.get("data", {})))
        except Exception as e:
            logger.warning(f"SerpApi Maps OSINT failed: {e}")
            bundle["errors"].append(str(e))
        
        try:
            social = await self.serpapi.discover_social_profiles(business_name, domain)
            bundle["social_discovery"] = social
            for result in social.get("results", []):
                bundle["organic_sources"].extend(self.serpapi.normalize_organic_results(result, source_type="social_search"))
        except Exception as e:
            logger.warning(f"SerpApi social discovery failed: {e}")
            bundle["errors"].append(str(e))
        
        return bundle
    
    def _normalize_osint_sources(
        self,
        scraped_pages: List[Dict[str, Any]],
        tavily_results: List[Dict[str, Any]],
        serpapi_bundle: Dict[str, Any],
    ) -> List[OSINTSource]:
        sources: List[OSINTSource] = []
        for page in scraped_pages:
            sources.append(OSINTSource(
                tool=page.get("strategy", "http"),
                source_type="website",
                title=page.get("title", ""),
                url=page.get("url", ""),
                snippet=(page.get("meta_description") or page.get("text", ""))[:500],
                score=0.95,
            ))
        for result in tavily_results:
            for item in result.get("results", [])[: settings.TAVILY_MAX_RESULTS]:
                sources.append(OSINTSource(
                    tool="tavily",
                    source_type=self._classify_source(item.get("url", "")),
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", item.get("snippet", ""))[:500],
                    score=float(item.get("score", 0.65) or 0.65),
                ))
        for item in serpapi_bundle.get("organic_sources", []) + serpapi_bundle.get("maps_sources", []):
            sources.append(OSINTSource(
                tool="serpapi",
                source_type=item.get("source_type") or self._classify_source(item.get("url", "")),
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("snippet", ""),
                score=0.8 if item.get("source_type") == "google_maps" else 0.7,
            ))
        return self._dedupe_sources(sources)
    
    async def _firecrawl_discovered_sources(self, sources: List[OSINTSource]) -> List[Dict[str, Any]]:
        if not settings.FIRECRAWL_API_KEY:
            return []
        candidates = [
            s for s in sources
            if s.url and s.source_type in {"social", "review", "directory", "competitor", "search"}
        ][: settings.MAX_OSINT_PAGES]
        pages = []
        for source in candidates:
            try:
                page = await self.scraper._scrape_firecrawl(source.url)
                page["source_type"] = source.source_type
                pages.append(page)
            except Exception as e:
                logger.debug(f"Firecrawl enrichment skipped for {source.url}: {e}")
        return pages
    
    def _dedupe_sources(self, sources: List[OSINTSource]) -> List[OSINTSource]:
        seen = set()
        deduped = []
        for source in sorted(sources, key=lambda s: s.score, reverse=True):
            key = (source.url or source.title).strip().lower().rstrip("/")
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(source)
        return deduped[:80]
    
    def _classify_source(self, url: str) -> str:
        value = (url or "").lower()
        if any(host in value for host in ["instagram.com", "linkedin.com", "facebook.com", "twitter.com", "x.com", "youtube.com", "tiktok.com"]):
            return "social"
        if any(host in value for host in ["google.com/maps", "yelp.", "tripadvisor.", "trustpilot.", "g2.com", "reviews"]):
            return "review"
        if any(word in value for word in ["competitor", "alternative", "directory", "clutch.co", "crunchbase.com"]):
            return "competitor"
        return "search"
    
    def _extract_social_profiles(self, sources: List[OSINTSource]) -> List[SocialProfile]:
        profiles = []
        platform_patterns = {
            "Instagram": "instagram.com",
            "LinkedIn": "linkedin.com",
            "Facebook": "facebook.com",
            "X": ("twitter.com", "x.com"),
            "YouTube": "youtube.com",
            "TikTok": "tiktok.com",
        }
        for source in sources:
            url = source.url.lower()
            for platform, pattern in platform_patterns.items():
                patterns = pattern if isinstance(pattern, tuple) else (pattern,)
                if any(p in url for p in patterns):
                    profiles.append(SocialProfile(
                        platform=platform,
                        url=source.url,
                        title=source.title,
                        snippet=source.snippet,
                        confidence=min(1.0, source.score + 0.15),
                    ))
                    break
        deduped = {}
        for profile in profiles:
            deduped.setdefault(profile.url, profile)
        return list(deduped.values())[:12]
    
    def _extract_locations(self, serpapi_bundle: Dict[str, Any]) -> List[BusinessLocation]:
        locations = []
        for item in serpapi_bundle.get("maps_sources", []):
            gps = item.get("gps_coordinates") or {}
            locations.append(BusinessLocation(
                name=item.get("title", ""),
                address=item.get("address"),
                phone=item.get("phone"),
                website=item.get("url"),
                category=item.get("category"),
                rating=item.get("rating"),
                reviews=item.get("reviews"),
                place_id=item.get("place_id"),
                latitude=gps.get("latitude"),
                longitude=gps.get("longitude"),
            ))
        return locations[:8]
    
    def _extract_reviews_summary(self, serpapi_bundle: Dict[str, Any], sources: List[OSINTSource]) -> ReviewsSummary:
        locations = self._extract_locations(serpapi_bundle)
        rated = [l for l in locations if l.rating is not None]
        average_rating = round(sum(l.rating for l in rated) / len(rated), 2) if rated else None
        total_reviews = sum(l.reviews or 0 for l in locations) or None
        review_sources = [s.url for s in sources if s.source_type in {"review", "google_maps"} and s.url]
        themes = []
        snippets = " ".join(s.snippet.lower() for s in sources if s.source_type in {"review", "google_maps"})
        for theme in ["quality", "service", "community", "price", "location", "support", "experience"]:
            if theme in snippets:
                themes.append(theme)
        return ReviewsSummary(
            average_rating=average_rating,
            total_reviews=total_reviews,
            themes=themes[:6],
            source_urls=list(dict.fromkeys(review_sources))[:10],
        )
    
    def _extract_competitor_evidence(self, sources: List[OSINTSource]) -> List[OSINTSource]:
        return [
            s for s in sources
            if s.source_type == "competitor"
            or any(word in f"{s.title} {s.snippet}".lower() for word in ["competitor", "alternative", "similar"])
        ][:12]
    
    def _build_tool_coverage(
        self,
        scraped_pages: List[Dict[str, Any]],
        tavily_results: List[Dict[str, Any]],
        serpapi_bundle: Dict[str, Any],
        firecrawl_pages: List[Dict[str, Any]],
        osint_sources: List[OSINTSource],
    ) -> SearchToolCoverage:
        return SearchToolCoverage(
            serpapi=len(serpapi_bundle.get("organic_sources", [])) + len(serpapi_bundle.get("maps_sources", [])),
            tavily=sum(len(result.get("results", [])) for result in tavily_results),
            firecrawl=len(firecrawl_pages),
            website_pages=len(scraped_pages),
            total_sources=len(osint_sources) + len(firecrawl_pages),
        )
    
    async def _synthesize_research(
        self,
        url: str,
        scraped_pages: List[Dict[str, Any]],
        search_results: List[Dict[str, Any]],
        extra_context: str = ""
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
        
        search_content = self._format_search_context(search_results)
        if extra_context:
            search_content = (
                f"--- USER EXTRA CONTEXT ---\n{extra_context[:2000]}\n\n"
                f"{search_content}"
            )
        
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
    
    def _format_search_context(self, search_results: List[Dict[str, Any]]) -> str:
        """Build compact evidence context from normalized OSINT output."""
        sections = []
        normalized = next((r for r in search_results if r.get("tool") == "osint_normalized"), {})
        if normalized:
            coverage = normalized.get("coverage", {})
            sections.append(
                "--- OSINT COVERAGE ---\n"
                f"SerpApi sources: {coverage.get('serpapi', 0)}\n"
                f"Tavily sources: {coverage.get('tavily', 0)}\n"
                f"Firecrawl pages: {coverage.get('firecrawl', 0)}\n"
                f"Website pages: {coverage.get('website_pages', 0)}"
            )
            if normalized.get("locations"):
                locations = [self._as_dict(loc) for loc in normalized.get("locations", [])]
                sections.append("--- GOOGLE MAPS / LOCAL ---\n" + "\n".join(
                    f"- {loc.get('name', '')}: {loc.get('address', '')} | "
                    f"rating={loc.get('rating')} reviews={loc.get('reviews')} | {loc.get('website', '')}"
                    for loc in locations[:8]
                ))
            if normalized.get("social_profiles"):
                profiles = [self._as_dict(p) for p in normalized.get("social_profiles", [])]
                sections.append("--- PUBLIC SOCIAL PROFILES ---\n" + "\n".join(
                    f"- {p.get('platform', '')}: {p.get('url', '')} | {p.get('snippet', '')[:220]}"
                    for p in profiles[:12]
                ))
            if normalized.get("competitor_evidence"):
                competitors = [self._as_dict(s) for s in normalized.get("competitor_evidence", [])]
                sections.append("--- COMPETITOR SIGNALS ---\n" + "\n".join(
                    f"- {s.get('title', '')}: {s.get('url', '')} | {s.get('snippet', '')[:250]}"
                    for s in competitors[:10]
                ))
            sources = [self._as_dict(s) for s in normalized.get("sources", [])]
            sections.append("--- TOP OSINT SOURCES ---\n" + "\n".join(
                f"- [{s.get('tool', '')}/{s.get('source_type', '')}] {s.get('title', '')}: "
                f"{s.get('url', '')} | {s.get('snippet', '')[:300]}"
                for s in sources[:30]
            ))
        
        tavily = next((r for r in search_results if r.get("tool") == "tavily"), {})
        for result in tavily.get("results", [])[:4]:
            sections.append(
                "--- TAVILY ANSWER ---\n"
                f"Answer: {result.get('answer', '')}\n"
                + "\n".join([
                    f"- {item.get('title', '')}: {item.get('content', item.get('snippet', ''))[:350]}"
                    for item in result.get("results", [])[:5]
                ])
            )
        return "\n\n".join(sections)[:12000]
    
    def _as_dict(self, value: Any) -> Dict[str, Any]:
        """Normalize Pydantic models or dict-like values for prompt formatting."""
        if isinstance(value, dict):
            return value
        if hasattr(value, "model_dump"):
            return value.model_dump()
        return {}
    
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
        
        audience = []
        for p in data.get("audience", []):
            if isinstance(p, dict):
                audience.append(BuyerPersona(**p))
            else:
                logger.warning(f"Skipping malformed persona: {p}")
        
        brand_data = data.get("brand_voice", {})
        brand_voice = BrandVoice(
            tone=brand_data.get("tone", "Professional"),
            style=brand_data.get("style", "Clear"),
            keywords=brand_data.get("keywords", []),
            avoid=brand_data.get("avoid", []),
            examples=brand_data.get("examples", [])
        )
        
        competitors = []
        for c in data.get("competitors", []):
            if isinstance(c, dict):
                competitors.append(Competitor(**c))
            elif isinstance(c, str):
                competitors.append(Competitor(name=c, differentiator="Unknown"))
            else:
                logger.warning(f"Skipping malformed competitor: {c}")
        
        evidence_data = data.get("evidence", {})
        evidence = ResearchEvidence(
            source_urls=evidence_data.get("source_urls", [url]),
            quotes=evidence_data.get("quotes", []),
            search_queries_used=evidence_data.get("search_queries_used", [])
        )
        normalized = next((r for r in search_results if r.get("tool") == "osint_normalized"), {})
        osint_sources = [
            OSINTSource(**source)
            for source in normalized.get("sources", [])
            if isinstance(source, dict)
        ]
        locations = [
            BusinessLocation(**location)
            for location in normalized.get("locations", [])
            if isinstance(location, dict)
        ]
        social_profiles = [
            SocialProfile(**profile)
            for profile in normalized.get("social_profiles", [])
            if isinstance(profile, dict)
        ]
        reviews_summary = ReviewsSummary(**normalized.get("reviews_summary", {}))
        coverage = SearchToolCoverage(**normalized.get("coverage", {}))
        competitor_evidence = [
            OSINTSource(**source)
            for source in normalized.get("competitor_evidence", [])
            if isinstance(source, dict)
        ]
        source_urls = list(dict.fromkeys(
            evidence.source_urls
            + [s.url for s in osint_sources if s.url]
            + [p.get("url", "") for p in scraped_pages if p.get("url")]
        ))
        evidence.source_urls = source_urls[:60]
        
        # Apply fallback extraction if structured fields are empty
        summary_text = data.get("summary", "")
        if business.name == "Unknown" or not business.description:
            business, brand_voice, audience, competitors = self._fallback_extract_from_summary(
                business, brand_voice, audience, competitors, summary_text, url
            )
        
        return ResearchResult(
            business=business,
            audience=audience,
            brand_voice=brand_voice,
            competitors=competitors,
            content_examples=data.get("content_examples", []),
            evidence=evidence,
            locations=locations,
            social_profiles=social_profiles,
            reviews_summary=reviews_summary,
            osint_sources=osint_sources,
            search_tool_coverage=coverage,
            competitor_evidence=competitor_evidence,
            research_depth="deep_osint",
            raw_data={
                "scraped_pages": len(scraped_pages),
                "search_results": len(search_results),
                "coverage": coverage.model_dump(),
                "timestamp": datetime.utcnow().isoformat()
            },
            confidence_score=data.get("confidence_score", 0.5),
            summary=summary_text
        )
    
    def _fallback_extract_from_summary(
        self,
        business: BusinessProfile,
        brand_voice: BrandVoice,
        audience: List[BuyerPersona],
        competitors: List[Competitor],
        summary: str,
        url: str
    ) -> tuple:
        """Extract structured data from summary when JSON fields are empty."""
        if not summary:
            return business, brand_voice, audience, competitors
        
        # Extract business name from URL if unknown
        if business.name == "Unknown" or not business.name:
            domain = url.replace("https://", "").replace("http://", "").split("/")[0]
            business.name = domain.replace("www.", "").split(".")[0].capitalize()
        
        # Use summary as description if empty
        if not business.description:
            business.description = summary[:500]
        
        # Extract industry from summary
        if business.industry == "Unknown":
            industries = ["coworking", "software", "AI", "technology", "marketing", 
                         "consulting", "e-commerce", "healthcare", "fintech", "education"]
            summary_lower = summary.lower()
            for ind in industries:
                if ind in summary_lower:
                    business.industry = ind.capitalize()
                    break
            if business.industry == "Unknown":
                business.industry = "Business Services"
        
        # Extract niche
        if business.niche == "Unknown":
            business.niche = business.industry
        
        # Extract value proposition from summary
        if not business.value_proposition:
            # Take first sentence or first 150 chars
            first_sent = summary.split(".")[0] if "." in summary else summary[:150]
            business.value_proposition = first_sent.strip()
        
        # Derive brand voice from summary
        if brand_voice.tone == "Professional" and not brand_voice.keywords:
            # Simple heuristic extraction
            summary_lower = summary.lower()
            empowering = any(w in summary_lower for w in ["empower", "community", "belong", "connect", "growth"])
            playful = any(w in summary_lower for w in ["fun", "playful", "creative", "innovative"])
            formal = any(w in summary_lower for w in ["enterprise", "solution", "corporate", "professional"])
            
            if empowering:
                brand_voice.tone = "Empowering and Community-Centric"
                brand_voice.keywords = ["community", "growth", "connection", "focus"]
            elif playful:
                brand_voice.tone = "Playful and Creative"
            elif formal:
                brand_voice.tone = "Professional and Formal"
        
        # Create a generic persona if none found
        if not audience:
            audience.append(BuyerPersona(
                persona="Target Customer",
                demographics="Professionals and businesses",
                pain_points=["Need for workspace", "Community", "Productivity"],
                goals=["Grow business", "Network", "Focus"],
                channels=["LinkedIn", "Instagram", "Website"]
            ))
        
        return business, brand_voice, audience, competitors
