"""Pydantic models for Phase 4: Self-Verification."""
from typing import List, Optional
from pydantic import BaseModel, Field

class CheckResult(BaseModel):
    check_name: str = Field(description="Name of the check")
    status: str = Field(description="PASS | FAIL | WARNING")
    score: float = Field(ge=0.0, le=1.0, description="Score 0.0-1.0")
    issues: List[str] = Field(default_factory=list, description="Specific issues found")
    suggestions: List[str] = Field(default_factory=list, description="Suggested fixes")
    evidence: Optional[str] = Field(None, description="Evidence for the score")

class VerificationResult(BaseModel):
    content_id: int = Field(description="Calendar item index")
    overall_status: str = Field(description="PASS | FAIL | NEEDS_REVIEW")
    overall_score: float = Field(ge=0.0, le=1.0, description="Weighted overall score")
    
    # Individual checks
    brand_alignment: CheckResult
    fact_check: CheckResult
    format_compliance: CheckResult
    quality_check: CheckResult
    engagement_prediction: Optional[CheckResult] = None
    
    # Iteration tracking
    iteration: int = Field(1, description="Which refinement iteration")
    max_iterations: int = Field(3, description="Max allowed iterations")
    was_modified: bool = Field(False, description="Was content modified in this iteration")
    modifications_made: List[str] = Field(default_factory=list, description="What was changed")
    
    # Final output
    final_content: Optional[str] = Field(None, description="Verified/finalized content")
    rejected: bool = Field(False, description="Content rejected after max iterations")
    rejection_reason: Optional[str] = Field(None, description="Why content was rejected")

class PipelineVerificationReport(BaseModel):
    results: List[VerificationResult] = Field(default_factory=list)
    total_checked: int = Field(0)
    total_passed: int = Field(0)
    total_failed: int = Field(0)
    total_modified: int = Field(0)
    total_rejected: int = Field(0)
    average_score: float = Field(0.0)
    report_summary: str = Field(description="Executive summary of verification")
    critical_issues: List[str] = Field(default_factory=list, description="Issues requiring human attention")
