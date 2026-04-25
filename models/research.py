"""Pydantic models for Phase 1: Research & Discovery."""
from typing import List, Optional
from pydantic import BaseModel, Field

class Competitor(BaseModel):
    name: str = Field(description="Competitor company name")
    url: Optional[str] = Field(None, description="Competitor website URL")
    differentiator: str = Field(description="How the target business differs from this competitor")

class BuyerPersona(BaseModel):
    persona: str = Field(description="Persona name/title")
    demographics: str = Field(description="Age, location, industry, company size")
    pain_points: List[str] = Field(default_factory=list, description="Key problems this persona faces")
    goals: List[str] = Field(default_factory=list, description="What this persona wants to achieve")
    channels: List[str] = Field(default_factory=list, description="Where this persona spends time online")

class BrandVoice(BaseModel):
    tone: str = Field(description="Overall tone of voice")
    style: str = Field(description="Writing style characteristics")
    keywords: List[str] = Field(default_factory=list, description="Words and phrases the brand commonly uses")
    avoid: List[str] = Field(default_factory=list, description="Words, phrases, or tones to avoid")
    examples: List[str] = Field(default_factory=list, description="Example sentences/phrases from real content")

class ResearchEvidence(BaseModel):
    source_urls: List[str] = Field(default_factory=list)
    quotes: List[str] = Field(default_factory=list, description="Direct quotes from sources")
    search_queries_used: List[str] = Field(default_factory=list)

class BusinessLocation(BaseModel):
    name: str = Field(default="", description="Location or listing name")
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    category: Optional[str] = None
    rating: Optional[float] = None
    reviews: Optional[int] = None
    place_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class SocialProfile(BaseModel):
    platform: str = Field(description="Platform name, e.g. Instagram or LinkedIn")
    url: str = Field(description="Public profile URL")
    title: Optional[str] = None
    snippet: Optional[str] = None
    confidence: float = Field(0.5, ge=0.0, le=1.0)

class ReviewsSummary(BaseModel):
    average_rating: Optional[float] = None
    total_reviews: Optional[int] = None
    themes: List[str] = Field(default_factory=list)
    source_urls: List[str] = Field(default_factory=list)

class OSINTSource(BaseModel):
    tool: str = Field(description="Tool used, e.g. serpapi, tavily, firecrawl, http")
    source_type: str = Field(description="Source category, e.g. website, google_maps, social")
    title: str = ""
    url: str = ""
    snippet: str = ""
    score: float = Field(0.0, ge=0.0, le=1.0)

class SearchToolCoverage(BaseModel):
    serpapi: int = 0
    tavily: int = 0
    firecrawl: int = 0
    website_pages: int = 0
    total_sources: int = 0

class BusinessProfile(BaseModel):
    name: str = Field(description="Company name")
    tagline: Optional[str] = Field(None, description="Company tagline or one-liner")
    description: str = Field(description="What the company does")
    industry: str = Field(description="Industry/category")
    niche: str = Field(description="Specific niche within the industry")
    products: List[str] = Field(default_factory=list, description="Main products/services")
    value_proposition: str = Field(description="Core value proposition")
    target_market: str = Field(description="Primary target market")
    founded: Optional[str] = Field(None, description="Year founded if available")
    size: Optional[str] = Field(None, description="Company size if available")

class ResearchResult(BaseModel):
    business: BusinessProfile
    audience: List[BuyerPersona] = Field(default_factory=list)
    brand_voice: BrandVoice
    competitors: List[Competitor] = Field(default_factory=list)
    content_examples: List[str] = Field(default_factory=list, description="Existing content samples for few-shot")
    evidence: ResearchEvidence
    locations: List[BusinessLocation] = Field(default_factory=list)
    social_profiles: List[SocialProfile] = Field(default_factory=list)
    reviews_summary: ReviewsSummary = Field(default_factory=ReviewsSummary)
    osint_sources: List[OSINTSource] = Field(default_factory=list)
    search_tool_coverage: SearchToolCoverage = Field(default_factory=SearchToolCoverage)
    competitor_evidence: List[OSINTSource] = Field(default_factory=list)
    research_depth: str = Field("standard", description="Research breadth/depth descriptor")
    raw_data: Optional[dict] = Field(None, description="Raw scraped/search data for debugging")
    confidence_score: float = Field(0.0, ge=0.0, le=1.0, description="Confidence in research quality")
    summary: str = Field(description="Executive summary of findings")
