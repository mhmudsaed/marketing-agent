"""Pydantic models for Phase 2: Strategy & Planning."""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import date

class ContentPillar(BaseModel):
    name: str = Field(description="Pillar name")
    description: str = Field(description="What this pillar covers")
    percentage: int = Field(description="Approximate % of content for this pillar")
    topics: List[str] = Field(default_factory=list, description="Sample topics under this pillar")

class ChannelStrategy(BaseModel):
    channel: str = Field(description="Channel name (LinkedIn, X, Instagram, Blog, etc.)")
    purpose: str = Field(description="Why this channel is chosen")
    audience_fit: str = Field(description="How the audience uses this channel")
    content_types: List[str] = Field(default_factory=list, description="Best content types for this channel")
    optimal_times: List[str] = Field(default_factory=list, description="Best posting times")
    frequency: str = Field(description="Posting frequency")

class CalendarItem(BaseModel):
    date: str = Field(description="Post date (YYYY-MM-DD)")
    time: str = Field(description="Post time (HH:MM)")
    channel: str = Field(description="Target channel")
    pillar: str = Field(description="Content pillar")
    topic: str = Field(description="Specific topic/title")
    format: str = Field(description="Content format (carousel, single, thread, blog, etc.)")
    cta: str = Field(description="Call-to-action")
    objective: str = Field(description="What this post aims to achieve")
    target_persona: str = Field(description="Which persona this targets")
    status: str = Field(default="planned", description="planned | generated | verified | published")

class StrategyResult(BaseModel):
    pillars: List[ContentPillar] = Field(default_factory=list)
    channels: List[ChannelStrategy] = Field(default_factory=list)
    calendar: List[CalendarItem] = Field(default_factory=list)
    overall_strategy: str = Field(description="Summary of the content strategy")
    rationale: str = Field(description="Why this strategy was chosen based on research")
