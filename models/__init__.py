"""Shared model types."""
from typing import Any, Optional
from pydantic import BaseModel, Field

class PipelineState(BaseModel):
    """Central state container for the entire pipeline."""
    business_url: str = Field(description="Input business URL")
    business_name: Optional[str] = Field(None, description="Resolved business name")
    
    # Phase outputs
    research: Optional[Any] = Field(None, description="Phase 1 output")
    strategy: Optional[Any] = Field(None, description="Phase 2 output")
    content: Optional[Any] = Field(None, description="Phase 3 output")
    verification: Optional[Any] = Field(None, description="Phase 4 output")
    
    # Metadata
    session_id: str = Field(description="Unique session ID")
    started_at: str = Field(description="ISO timestamp of start")
    completed_at: Optional[str] = Field(None, description="ISO timestamp of completion")
    errors: list[str] = Field(default_factory=list, description="Non-fatal errors encountered")
    status: str = Field(default="initialized", description="Pipeline status")
    
    class Config:
        arbitrary_types_allowed = True
