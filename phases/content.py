"""Phase 3: Content Generation engine."""
import time
from typing import Optional, List
from clients.openrouter import OpenRouterClient
from models.research import ResearchResult
from models.strategy import StrategyResult, CalendarItem
from models.content import GeneratedContent, ContentPackage
from utils.prompts import CONTENT_SYSTEM_PROMPT, CONTENT_USER_PROMPT
from utils.validators import ContentValidator
from utils.logger import logger
from config.settings import settings

class ContentEngine:
    """Enterprise-grade content generation engine."""
    
    def __init__(self, llm: Optional[OpenRouterClient] = None):
        self.llm = llm or OpenRouterClient()
        logger.info("ContentEngine initialized")
    
    async def run(
        self,
        research: ResearchResult,
        strategy: StrategyResult
    ) -> ContentPackage:
        """
        Generate content for all calendar items.
        
        1. Generate content per calendar item with brand-aware prompts
        2. Generate variants for quality selection
        3. Compute metadata (word count, char count, etc.)
        """
        logger.info(f"✍️ Generating content for {len(strategy.calendar)} posts")
        
        contents = []
        for idx, item in enumerate(strategy.calendar):
            logger.info(f"  [{idx+1}/{len(strategy.calendar)}] {item.channel}: {item.topic}")
            
            try:
                content = await self._generate_single_content(
                    research, strategy, item, idx
                )
                contents.append(content)
            except Exception as e:
                logger.error(f"Failed to generate content for item {idx}: {e}")
                # Add placeholder
                contents.append(self._placeholder_content(item, idx))
        
        package = ContentPackage(
            contents=contents,
            package_summary=f"Generated {len(contents)} posts for {research.business.name}",
            total_posts=len(contents),
            channels_covered=list(set(c.channel for c in contents)),
            estimated_total_reach="TBD"
        )
        
        logger.info(
            f"✅ Content generation complete | posts={package.total_posts} | "
            f"channels={package.channels_covered}"
        )
        
        return package
    
    async def _generate_single_content(
        self,
        research: ResearchResult,
        strategy: StrategyResult,
        item: CalendarItem,
        idx: int
    ) -> GeneratedContent:
        """Generate content for a single calendar item."""
        
        # Get target persona
        persona = next(
            (p for p in research.audience if p.persona == item.target_persona),
            research.audience[0] if research.audience else None
        )
        
        # Build prompt
        user_prompt = CONTENT_USER_PROMPT.format(
            business_name=research.business.name,
            tagline=research.business.tagline or "",
            value_proposition=research.business.value_proposition,
            tone=research.brand_voice.tone,
            style=research.brand_voice.style,
            keywords=", ".join(research.brand_voice.keywords[:10]),
            avoid=", ".join(research.brand_voice.avoid[:5]),
            examples="\n".join(research.brand_voice.examples[:3]),
            persona=persona.persona if persona else "General audience",
            pain_points=", ".join(persona.pain_points[:3]) if persona else "",
            channel=item.channel,
            format=item.format,
            topic=item.topic,
            objective=item.objective,
            cta=item.cta
        )
        
        start = time.time()
        
        # Generate main content
        content_text = await self.llm.generate_text(
            system_prompt=CONTENT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.8,
            max_tokens=2000
        )
        
        # Extract components
        headline, body, extracted_cta = self._parse_content(content_text, item.cta)
        
        # Generate variants if configured
        variants = []
        if settings.MAX_CONTENT_VARIANTS > 1:
            variants = await self._generate_variants(
                user_prompt, settings.MAX_CONTENT_VARIANTS - 1
            )
        
        elapsed = int((time.time() - start) * 1000)
        
        return GeneratedContent(
            calendar_item_id=idx,
            channel=item.channel,
            format=item.format,
            topic=item.topic,
            headline=headline,
            body=body,
            cta=extracted_cta or item.cta,
            hashtags=ContentValidator.extract_hashtags(content_text),
            image_prompt=self._generate_image_prompt(research, item, content_text),
            suggested_image_style=self._suggest_image_style(item.channel),
            word_count=ContentValidator.count_words(content_text),
            char_count=ContentValidator.count_chars(content_text),
            reading_time=self._estimate_reading_time(content_text),
            variants=variants,
            model_used=self.llm.model,
            generation_time_ms=elapsed
        )
    
    async def _generate_variants(
        self,
        base_prompt: str,
        count: int
    ) -> List[str]:
        """Generate alternative versions."""
        variants = []
        variant_prompt = base_prompt + "\n\nWrite a DIFFERENT version with a different angle or hook. Same topic, fresh approach."
        
        for i in range(count):
            try:
                variant = await self.llm.generate_text(
                    system_prompt=CONTENT_SYSTEM_PROMPT,
                    user_prompt=variant_prompt,
                    temperature=0.9,
                    max_tokens=1500
                )
                variants.append(variant)
            except Exception as e:
                logger.warning(f"Variant {i+1} generation failed: {e}")
                break
        
        return variants
    
    def _parse_content(self, text: str, default_cta: str) -> tuple:
        """Parse generated content into headline, body, CTA."""
        lines = text.strip().split("\n")
        
        # First non-empty line is headline/hook
        headline = ""
        body_start = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped:
                headline = stripped
                body_start = i + 1
                break
        
        body = "\n".join(lines[body_start:]).strip()
        
        # Try to extract CTA from last line
        cta = default_cta
        if lines and len(lines) > 2:
            last_lines = [l.strip() for l in lines[-3:] if l.strip()]
            if last_lines:
                # Simple heuristic: last line might be CTA if short and action-oriented
                last = last_lines[-1]
                if len(last) < 150 and any(w in last.lower() for w in ["click", "learn", "try", "get", "visit", "sign", "download", "follow"]):
                    cta = last
        
        return headline, body, cta
    
    def _generate_image_prompt(
        self,
        research: ResearchResult,
        item: CalendarItem,
        content: str
    ) -> str:
        """Generate an AI image prompt."""
        return (
            f"Professional marketing image for {research.business.name}. "
            f"Topic: {item.topic}. "
            f"Style: {research.brand_voice.tone}, modern, clean. "
            f"No text in image. Relevant visual metaphor."
        )
    
    def _suggest_image_style(self, channel: str) -> str:
        """Suggest image style per channel."""
        styles = {
            "LinkedIn": "Professional infographic or clean photography, 1200x627px",
            "X": "Bold graphic with minimal text, 1600x900px",
            "Twitter": "Bold graphic with minimal text, 1600x900px",
            "Instagram": "Square lifestyle photo or carousel, 1080x1080px",
            "Blog": "Wide header image, 1200x630px, contextual photography"
        }
        return styles.get(channel, "Professional marketing image, 1200x627px")
    
    def _estimate_reading_time(self, text: str) -> str:
        """Estimate reading time."""
        words = ContentValidator.count_words(text)
        minutes = max(1, round(words / 200))
        return f"{minutes} min read" if minutes > 1 else "< 1 min"
    
    def _placeholder_content(self, item: CalendarItem, idx: int) -> GeneratedContent:
        """Create placeholder content for failed generation."""
        return GeneratedContent(
            calendar_item_id=idx,
            channel=item.channel,
            format=item.format,
            topic=item.topic,
            headline=f"Content about {item.topic}",
            body=f"[Content generation failed for {item.topic}. Manual creation required.]",
            cta=item.cta,
            model_used="ERROR",
            generation_time_ms=0
        )
