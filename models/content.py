"""Pydantic models for Phase 3: Content Generation."""
from typing import List, Optional
from pydantic import BaseModel, Field

class GeneratedContent(BaseModel):
    calendar_item_id: int = Field(description="Index of the calendar item")
    channel: str = Field(description="Target channel")
    format: str = Field(description="Content format")
    topic: str = Field(description="Topic")
    
    # Main content
    headline: str = Field(description="Attention-grabbing headline/hook")
    body: str = Field(description="Main content body")
    cta: str = Field(description="Call-to-action text")
    hashtags: List[str] = Field(default_factory=list, description="Relevant hashtags")
    
    # Assets
    image_prompt: Optional[str] = Field(None, description="AI image generation prompt")
    suggested_image_style: Optional[str] = Field(None, description="Visual style recommendation")
    
    # Metadata
    word_count: int = Field(0, description="Content word count")
    char_count: int = Field(0, description="Content character count")
    reading_time: Optional[str] = Field(None, description="Estimated reading time")
    
    # Variants for A/B testing
    variants: List[str] = Field(default_factory=list, description="Alternative versions")
    
    # Generation metadata
    model_used: str = Field(description="LLM model used")
    generation_time_ms: Optional[int] = Field(None, description="Generation time")

class ContentPackage(BaseModel):
    contents: List[GeneratedContent] = Field(default_factory=list)
    package_summary: str = Field(description="Summary of all generated content")
    total_posts: int = Field(0)
    channels_covered: List[str] = Field(default_factory=list)
    estimated_total_reach: Optional[str] = Field(None, description="Estimated audience reach")
