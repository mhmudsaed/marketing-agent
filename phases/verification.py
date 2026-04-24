"""Phase 4: Self-Verification engine with auto-refinement."""
import json
from typing import Optional
from clients.openrouter import OpenRouterClient
from models.research import ResearchResult
from models.strategy import StrategyResult
from models.content import GeneratedContent, ContentPackage
from models.verification import VerificationResult, CheckResult, PipelineVerificationReport
from utils.prompts import (
    VERIFICATION_SYSTEM_PROMPT, BRAND_ALIGNMENT_PROMPT, FACT_CHECK_PROMPT,
    FORMAT_CHECK_PROMPT, QUALITY_CHECK_PROMPT, REFINE_PROMPT, CHANNEL_REQUIREMENTS
)
from utils.validators import ContentValidator
from utils.logger import logger
from config.settings import settings

class VerificationEngine:
    """Enterprise-grade self-verification with auto-refinement loops."""
    
    def __init__(self, llm: Optional[OpenRouterClient] = None):
        self.llm = llm or OpenRouterClient()
        logger.info("VerificationEngine initialized")
    
    async def run(
        self,
        research: ResearchResult,
        strategy: StrategyResult,
        content_package: ContentPackage
    ) -> PipelineVerificationReport:
        """
        Verify all generated content with iterative refinement.
        
        For each piece of content:
        1. Run all checks (brand, facts, format, quality)
        2. If any fail, attempt auto-refinement
        3. Re-check after refinement
        4. Track iterations and final status
        """
        logger.info(f"🔍 Starting verification for {len(content_package.contents)} posts")
        
        results = []
        for idx, content in enumerate(content_package.contents):
            logger.info(f"  [{idx+1}/{len(content_package.contents)}] Verifying {content.channel} post...")
            
            try:
                result = await self._verify_single_content(
                    content, research, strategy, idx
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Verification failed for content {idx}: {e}")
                results.append(self._error_verification(content, idx, str(e)))
        
        # Compile report
        passed = sum(1 for r in results if r.overall_status == "PASS")
        failed = sum(1 for r in results if r.overall_status == "FAIL")
        modified = sum(1 for r in results if r.was_modified)
        rejected = sum(1 for r in results if r.rejected)
        avg_score = sum(r.overall_score for r in results) / max(len(results), 1)
        
        critical_issues = []
        for r in results:
            if r.rejection_reason:
                critical_issues.append(f"Post {r.content_id}: {r.rejection_reason}")
        
        report = PipelineVerificationReport(
            results=results,
            total_checked=len(results),
            total_passed=passed,
            total_failed=failed,
            total_modified=modified,
            total_rejected=rejected,
            average_score=round(avg_score, 2),
            report_summary=(
                f"Verified {len(results)} posts. "
                f"Passed: {passed}, Failed: {failed}, Modified: {modified}, Rejected: {rejected}. "
                f"Average score: {avg_score:.2f}/1.0"
            ),
            critical_issues=critical_issues
        )
        
        logger.info(
            f"✅ Verification complete | passed={passed}/{len(results)} | "
            f"modified={modified} | rejected={rejected} | avg_score={avg_score:.2f}"
        )
        
        return report
    
    async def _verify_single_content(
        self,
        content: GeneratedContent,
        research: ResearchResult,
        strategy: StrategyResult,
        idx: int
    ) -> VerificationResult:
        """Verify a single content piece with refinement loop."""
        
        current_text = f"{content.headline}\n\n{content.body}"
        iteration = 1
        max_iterations = settings.MAX_VERIFICATION_RETRIES
        
        while iteration <= max_iterations:
            # Run all checks
            brand_check = await self._check_brand_alignment(current_text, research)
            fact_check = await self._check_facts(current_text, research)
            format_check = await self._check_format(current_text, content)
            quality_check = await self._check_quality(current_text, content)
            
            # Calculate weighted overall score
            overall_score = (
                brand_check.score * 0.30 +
                fact_check.score * 0.25 +
                format_check.score * 0.25 +
                quality_check.score * 0.20
            )
            
            # Determine status
            statuses = [brand_check.status, fact_check.status, format_check.status, quality_check.status]
            if all(s == "PASS" for s in statuses):
                overall_status = "PASS"
            elif "FAIL" in statuses and iteration == max_iterations:
                overall_status = "FAIL"
            elif "FAIL" in statuses:
                overall_status = "NEEDS_REFINEMENT"
            else:
                overall_status = "NEEDS_REVIEW"
            
            # If pass or last iteration, return
            if overall_status == "PASS" or iteration == max_iterations:
                return VerificationResult(
                    content_id=idx,
                    overall_status="PASS" if overall_status == "PASS" else "FAIL",
                    overall_score=round(overall_score, 2),
                    brand_alignment=brand_check,
                    fact_check=fact_check,
                    format_compliance=format_check,
                    quality_check=quality_check,
                    iteration=iteration,
                    max_iterations=max_iterations,
                    was_modified=iteration > 1,
                    modifications_made=[],  # Could track these
                    final_content=current_text if overall_status == "PASS" else None,
                    rejected=overall_status != "PASS" and iteration == max_iterations,
                    rejection_reason=None if overall_status == "PASS" else "Failed verification after max iterations"
                )
            
            # Need refinement - collect all feedback
            logger.info(f"    ↻ Iteration {iteration} failed. Auto-refining...")
            
            feedback_parts = []
            for check in [brand_check, fact_check, format_check, quality_check]:
                if check.status != "PASS":
                    feedback_parts.append(f"[{check.check_name}] Issues: {'; '.join(check.issues)}")
            
            feedback = "\n".join(feedback_parts)
            
            # Attempt refinement
            try:
                refined = await self._refine_content(current_text, feedback, research)
                current_text = refined
                iteration += 1
            except Exception as e:
                logger.error(f"Refinement failed: {e}")
                iteration += 1  # Continue to next iteration or exit
        
        # Should not reach here, but safety fallback
        return self._error_verification(content, idx, "Max iterations exceeded")
    
    async def _check_brand_alignment(self, content: str, research: ResearchResult) -> CheckResult:
        """Check if content matches brand voice."""
        try:
            prompt = BRAND_ALIGNMENT_PROMPT.format(
                tone=research.brand_voice.tone,
                style=research.brand_voice.style,
                keywords=", ".join(research.brand_voice.keywords),
                avoid=", ".join(research.brand_voice.avoid),
                examples="\n".join(research.brand_voice.examples[:3]),
                content=content
            )
            
            result = await self.llm.generate_json(
                system_prompt=VERIFICATION_SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.2,
                max_tokens=1000
            )
            
            return CheckResult(**result)
        except Exception as e:
            logger.warning(f"Brand alignment LLM check failed: {e}")
            # Fallback to heuristic
            score = ContentValidator.calculate_brand_similarity(
                content,
                research.brand_voice.keywords,
                research.brand_voice.examples
            )
            return CheckResult(
                check_name="Brand Alignment",
                status="PASS" if score > 0.6 else "WARNING",
                score=score,
                issues=[] if score > 0.6 else ["Brand similarity below threshold"],
                suggestions=["Review brand voice consistency"] if score <= 0.6 else []
            )
    
    async def _check_facts(self, content: str, research: ResearchResult) -> CheckResult:
        """Check factual accuracy against research."""
        try:
            # Build facts reference
            facts = f"""
Business Name: {research.business.name}
Description: {research.business.description}
Products: {', '.join(research.business.products)}
Value Proposition: {research.business.value_proposition}
Industry: {research.business.industry}
Niche: {research.business.niche}
"""
            
            prompt = FACT_CHECK_PROMPT.format(
                business_facts=facts,
                content=content
            )
            
            result = await self.llm.generate_json(
                system_prompt=VERIFICATION_SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.2,
                max_tokens=1000
            )
            
            return CheckResult(**result)
        except Exception as e:
            logger.warning(f"Fact check LLM failed: {e}")
            return CheckResult(
                check_name="Fact Check",
                status="WARNING",
                score=0.7,
                issues=["Could not verify all facts automatically"],
                suggestions=["Manual review recommended"]
            )
    
    async def _check_format(self, content: str, generated: GeneratedContent) -> CheckResult:
        """Check format compliance per channel."""
        channel = generated.channel
        
        # Character limit
        within_limit, chars, limit = ContentValidator.check_char_limit(content, channel)
        
        # Hashtag count
        hashtag_ok, hashtag_count, max_hashtags = ContentValidator.check_hashtag_count(content, channel)
        
        # CTA presence
        cta_present = ContentValidator.check_cta_present(content, generated.cta)
        
        issues = []
        if not within_limit:
            issues.append(f"Character count {chars} exceeds {channel} limit of {limit}")
        if not hashtag_ok:
            issues.append(f"Hashtag count {hashtag_count} exceeds recommended {max_hashtags}")
        if not cta_present:
            issues.append("CTA may not be clearly present in content")
        
        score = 1.0
        if not within_limit:
            score -= 0.3
        if not hashtag_ok:
            score -= 0.2
        if not cta_present:
            score -= 0.1
        
        return CheckResult(
            check_name="Format Compliance",
            status="PASS" if score >= 0.8 else "FAIL" if score < 0.5 else "WARNING",
            score=round(score, 2),
            issues=issues,
            suggestions=["Adjust length", "Reduce hashtags", "Add clear CTA"] if issues else []
        )
    
    async def _check_quality(self, content: str, generated: GeneratedContent) -> CheckResult:
        """Check content quality."""
        try:
            prompt = QUALITY_CHECK_PROMPT.format(content=content)
            
            result = await self.llm.generate_json(
                system_prompt=VERIFICATION_SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.2,
                max_tokens=1000
            )
            
            return CheckResult(**result)
        except Exception as e:
            logger.warning(f"Quality check LLM failed: {e}")
            # Fallback heuristic
            readability = ContentValidator.calculate_readability(content)
            hook = ContentValidator.check_hook_strength(content)
            
            score = (readability["flesch_score"] / 100 * 0.3 + hook["score"] * 0.7)
            score = min(1.0, max(0.0, score))
            
            return CheckResult(
                check_name="Quality Check",
                status="PASS" if score > 0.6 else "WARNING",
                score=round(score, 2),
                issues=[],
                suggestions=["Review readability and hook strength"]
            )
    
    async def _refine_content(
        self,
        content: str,
        feedback: str,
        research: ResearchResult
    ) -> str:
        """Refine content based on verification feedback."""
        prompt = REFINE_PROMPT.format(
            original_content=content,
            feedback=feedback,
            tone=research.brand_voice.tone,
            style=research.brand_voice.style,
            keywords=", ".join(research.brand_voice.keywords)
        )
        
        refined = await self.llm.generate_text(
            system_prompt=CONTENT_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.7,
            max_tokens=2000
        )
        
        return refined
    
    def _error_verification(
        self,
        content: GeneratedContent,
        idx: int,
        error: str
    ) -> VerificationResult:
        """Create error verification result."""
        failed_check = CheckResult(
            check_name="System Error",
            status="FAIL",
            score=0.0,
            issues=[f"Verification system error: {error}"],
            suggestions=["Manual review required"]
        )
        
        return VerificationResult(
            content_id=idx,
            overall_status="FAIL",
            overall_score=0.0,
            brand_alignment=failed_check,
            fact_check=failed_check,
            format_compliance=failed_check,
            quality_check=failed_check,
            rejected=True,
            rejection_reason=f"System error during verification: {error}"
        )
