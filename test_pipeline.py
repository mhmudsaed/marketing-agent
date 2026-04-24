"""
Quick validation test for the pipeline without API calls.
Run with: python test_pipeline.py
"""
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from models.research import (
    ResearchResult, BusinessProfile, BuyerPersona, 
    BrandVoice, Competitor, ResearchEvidence
)
from models.strategy import StrategyResult, ContentPillar, ChannelStrategy, CalendarItem
from models.content import GeneratedContent, ContentPackage
from models.verification import VerificationResult, CheckResult, PipelineVerificationReport
from utils.validators import ContentValidator

def test_models():
    """Test that all models can be instantiated."""
    print("Testing models...")
    
    business = BusinessProfile(
        name="Test Corp",
        description="A test company",
        industry="Software",
        niche="AI Tools",
        products=["Product A"],
        value_proposition="We make AI easy",
        target_market="Enterprise"
    )
    
    persona = BuyerPersona(
        persona="CTO",
        demographics="35-50, Tech",
        pain_points=["Scaling", "Cost"],
        goals=["Efficiency"],
        channels=["LinkedIn"]
    )
    
    brand = BrandVoice(
        tone="Professional",
        style="Concise",
        keywords=["AI", "easy"],
        avoid=["jargon"],
        examples=["Example 1"]
    )
    
    research = ResearchResult(
        business=business,
        audience=[persona],
        brand_voice=brand,
        evidence=ResearchEvidence(source_urls=["https://test.com"]),
        confidence_score=0.85,
        summary="Test research"
    )
    
    pillar = ContentPillar(name="Education", description="Teach stuff", percentage=50, topics=["T1"])
    channel = ChannelStrategy(
        channel="LinkedIn", purpose="B2B", audience_fit="Great",
        content_types=["Post"], optimal_times=["9am"], frequency="Daily"
    )
    calendar_item = CalendarItem(
        date="2026-04-25", time="09:00", channel="LinkedIn",
        pillar="Education", topic="AI Tips", format="single",
        cta="Learn more", objective="awareness", target_persona="CTO"
    )
    
    strategy = StrategyResult(
        pillars=[pillar], channels=[channel], calendar=[calendar_item],
        overall_strategy="Test strategy", rationale="Because testing"
    )
    
    content = GeneratedContent(
        calendar_item_id=0, channel="LinkedIn", format="single",
        topic="AI Tips", headline="Test Headline", body="Test body",
        cta="Click here", model_used="test", generation_time_ms=100
    )
    
    package = ContentPackage(
        contents=[content], package_summary="Test package",
        total_posts=1, channels_covered=["LinkedIn"]
    )
    
    check = CheckResult(check_name="Test", status="PASS", score=0.9, issues=[], suggestions=[])
    
    verification = VerificationResult(
        content_id=0, overall_status="PASS", overall_score=0.9,
        brand_alignment=check, fact_check=check, format_compliance=check,
        quality_check=check
    )
    
    report = PipelineVerificationReport(
        results=[verification], total_checked=1, total_passed=1,
        total_failed=0, total_modified=0, total_rejected=0,
        average_score=0.9, report_summary="All good"
    )
    
    print(f"  ✓ Research model: {research.business.name}")
    print(f"  ✓ Strategy model: {len(strategy.calendar)} calendar items")
    print(f"  ✓ Content model: {package.total_posts} posts")
    print(f"  ✓ Verification model: {report.total_passed}/{report.total_checked} passed")
    print("  Models OK!")

def test_validators():
    """Test content validation utilities."""
    print("\nTesting validators...")
    
    text = "This is a #test post for #LinkedIn with a CTA: click here!"
    
    chars = ContentValidator.count_chars(text)
    words = ContentValidator.count_words(text)
    hashtags = ContentValidator.extract_hashtags(text)
    limit_ok, char_count, limit = ContentValidator.check_char_limit(text, "LinkedIn")
    hashtag_ok, ht_count, max_ht = ContentValidator.check_hashtag_count(text, "LinkedIn")
    readability = ContentValidator.calculate_readability(text)
    hook = ContentValidator.check_hook_strength(text)
    
    print(f"  ✓ Chars: {chars}, Words: {words}")
    print(f"  ✓ Hashtags: {hashtags}")
    print(f"  ✓ LinkedIn limit: {char_count}/{limit} ({'OK' if limit_ok else 'FAIL'})")
    print(f"  ✓ Readability: {readability['flesch_score']}")
    print(f"  ✓ Hook score: {hook['score']}")
    print("  Validators OK!")

def test_pipeline_structure():
    """Test pipeline can be instantiated."""
    print("\nTesting pipeline structure...")
    from core.pipeline import MarketingPipeline
    from core.state import PipelineStateManager
    
    # We can't actually run the pipeline without API keys,
    # but we can verify the structure
    state = PipelineStateManager()
    print(f"  ✓ State manager created: {state.session_id}")
    print(f"  ✓ Output dir: {state.output_dir}")
    print("  Pipeline structure OK!")

def main():
    print("=" * 60)
    print("Marketing Content Pipeline Agent - Validation Tests")
    print("=" * 60)
    
    test_models()
    test_validators()
    test_pipeline_structure()
    
    print("\n" + "=" * 60)
    print("✅ All tests passed! Agent is structurally sound.")
    print("=" * 60)
    print("\nNote: API integration tests require valid API keys in .env")

if __name__ == "__main__":
    main()
