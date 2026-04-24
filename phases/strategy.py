"""Phase 2: Strategy & Planning engine."""
from typing import Optional
from datetime import datetime, timedelta
from clients.openrouter import OpenRouterClient
from models.research import ResearchResult
from models.strategy import StrategyResult, ContentPillar, ChannelStrategy, CalendarItem
from utils.prompts import STRATEGY_SYSTEM_PROMPT, STRATEGY_USER_PROMPT
from utils.logger import logger
from config.settings import settings

class StrategyEngine:
    """Enterprise-grade content strategy engine."""
    
    def __init__(self, llm: Optional[OpenRouterClient] = None):
        self.llm = llm or OpenRouterClient()
        logger.info("StrategyEngine initialized")
    
    async def run(self, research: ResearchResult) -> StrategyResult:
        """
        Generate content strategy from research.
        
        1. Generate pillars and channel strategy via LLM
        2. Build calendar
        3. Validate and structure
        """
        logger.info(f"📋 Generating strategy for: {research.business.name}")
        
        # Step 1: LLM-generated strategy
        strategy_data = await self._generate_strategy_with_llm(research)
        
        # Step 2: Build calendar if not provided by LLM
        calendar = strategy_data.get("calendar", [])
        if not calendar:
            calendar = self._build_calendar(
                strategy_data.get("pillars", []),
                strategy_data.get("channels", []),
                research
            )
        
        # Step 3: Parse into models
        result = StrategyResult(
            pillars=[ContentPillar(**p) for p in strategy_data.get("pillars", [])],
            channels=[ChannelStrategy(**c) for c in strategy_data.get("channels", [])],
            calendar=[CalendarItem(**c) for c in calendar],
            overall_strategy=strategy_data.get("overall_strategy", ""),
            rationale=strategy_data.get("rationale", "")
        )
        
        logger.info(
            f"✅ Strategy complete | pillars={len(result.pillars)} | "
            f"channels={len(result.channels)} | posts={len(result.calendar)}"
        )
        
        return result
    
    async def _generate_strategy_with_llm(self, research: ResearchResult) -> dict:
        """Use LLM to generate strategy components."""
        
        # Serialize research for prompt
        business_json = research.business.model_dump_json(indent=2)
        audience_json = "\n".join([p.model_dump_json(indent=2) for p in research.audience])
        brand_json = research.brand_voice.model_dump_json(indent=2)
        
        user_prompt = STRATEGY_USER_PROMPT.format(
            research_summary=research.summary,
            business_profile=business_json,
            audience=audience_json,
            brand_voice=brand_json,
            calendar_days=settings.DEFAULT_CALENDAR_DAYS,
            posts_per_week=settings.DEFAULT_POSTS_PER_WEEK
        )
        
        logger.info("🧠 Generating strategy with LLM...")
        
        try:
            result = await self.llm.generate_json(
                system_prompt=STRATEGY_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.5,
                max_tokens=4000
            )
            return result
        except Exception as e:
            logger.error(f"Strategy generation failed: {e}")
            return self._fallback_strategy(research)
    
    def _build_calendar(
        self,
        pillars: list,
        channels: list,
        research: ResearchResult
    ) -> list:
        """Build a calendar if LLM didn't provide one."""
        logger.info("📅 Building fallback calendar")
        
        calendar = []
        start_date = datetime.now() + timedelta(days=1)
        days = settings.DEFAULT_CALENDAR_DAYS
        posts_per_week = settings.DEFAULT_POSTS_PER_WEEK
        
        channel_names = [c.get("channel", "LinkedIn") for c in channels] if channels else ["LinkedIn"]
        pillar_names = [p.get("name", "General") for p in pillars] if pillars else ["Product", "Education", "Industry"]
        
        # Generate posts spread across days
        total_posts = min(int(days / 7 * posts_per_week), 20)
        
        for i in range(total_posts):
            post_date = start_date + timedelta(days=i * (7 // posts_per_week))
            channel = channel_names[i % len(channel_names)]
            pillar = pillar_names[i % len(pillar_names)]
            
            calendar.append({
                "date": post_date.strftime("%Y-%m-%d"),
                "time": "09:00" if channel == "LinkedIn" else "14:00",
                "channel": channel,
                "pillar": pillar,
                "topic": f"{pillar} content for {research.business.name}",
                "format": "single" if channel in ["LinkedIn", "X"] else "carousel",
                "cta": f"Learn more about {research.business.name}",
                "objective": "awareness",
                "target_persona": research.audience[0].persona if research.audience else "General"
            })
        
        return calendar
    
    def _fallback_strategy(self, research: ResearchResult) -> dict:
        """Generate a basic fallback strategy if LLM fails."""
        logger.warning("Using fallback strategy")
        
        return {
            "pillars": [
                {
                    "name": "Product Education",
                    "description": "Teach audience about product capabilities",
                    "percentage": 40,
                    "topics": ["How-to guides", "Feature highlights", "Use cases"]
                },
                {
                    "name": "Industry Insights",
                    "description": "Share thought leadership and trends",
                    "percentage": 30,
                    "topics": ["Market trends", "Best practices", "Expert opinions"]
                },
                {
                    "name": "Community & Culture",
                    "description": "Build brand affinity and trust",
                    "percentage": 30,
                    "topics": ["Behind the scenes", "Customer stories", "Team spotlights"]
                }
            ],
            "channels": [
                {
                    "channel": "LinkedIn",
                    "purpose": "B2B professional audience",
                    "audience_fit": "Primary channel for business professionals",
                    "content_types": ["Articles", "Carousels", "Single posts"],
                    "optimal_times": ["09:00", "12:00"],
                    "frequency": "3x per week"
                }
            ],
            "calendar": [],
            "overall_strategy": "Focus on educational content that demonstrates expertise.",
            "rationale": "Generated as fallback due to LLM error."
        }
