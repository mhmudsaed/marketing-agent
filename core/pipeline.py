"""Pipeline orchestration engine."""
import asyncio
from typing import Optional
from clients.openrouter import OpenRouterClient
from clients.tavily import TavilyClient
from clients.scraper import WebScraper
from models.research import ResearchResult
from models.strategy import StrategyResult
from models.content import ContentPackage
from models.verification import PipelineVerificationReport
from phases.research import ResearchEngine
from phases.strategy import StrategyEngine
from phases.content import ContentEngine
from phases.verification import VerificationEngine
from core.state import PipelineStateManager
from utils.logger import logger
from config.settings import settings

class MarketingPipeline:
    """
    Enterprise-grade marketing content pipeline orchestrator.
    
    Executes the full pipeline:
    Research → Strategy → Content → Verification
    """
    
    def __init__(
        self,
        llm: Optional[OpenRouterClient] = None,
        search: Optional[TavilyClient] = None,
        scraper: Optional[WebScraper] = None,
        state_manager: Optional[PipelineStateManager] = None
    ):
        self.llm = llm or OpenRouterClient()
        self.search = search or TavilyClient()
        self.scraper = scraper or WebScraper()
        self.state = state_manager or PipelineStateManager()
        
        # Phase engines
        self.research_engine = ResearchEngine(self.llm, self.search, self.scraper)
        self.strategy_engine = StrategyEngine(self.llm)
        self.content_engine = ContentEngine(self.llm)
        self.verification_engine = VerificationEngine(self.llm)
        
        logger.info("🚀 MarketingPipeline initialized")
    
    async def run(self, business_url: str) -> dict:
        """
        Execute the full pipeline.
        
        Args:
            business_url: URL of the business to research
            
        Returns:
            Dict with all outputs and metadata
        """
        logger.info(f"🎯 Starting pipeline for: {business_url}")
        self.state.update(business_url=business_url, status="running")
        
        try:
            # Phase 1: Research
            logger.info("═" * 60)
            logger.info("PHASE 1: RESEARCH & DISCOVERY")
            logger.info("═" * 60)
            research = await self.research_engine.run(business_url)
            self.state.save_research(research)
            self.state.update(status="research_complete", business_name=research.business.name)
            
            # Phase 2: Strategy
            logger.info("═" * 60)
            logger.info("PHASE 2: STRATEGY & PLANNING")
            logger.info("═" * 60)
            strategy = await self.strategy_engine.run(research)
            self.state.save_strategy(strategy)
            self.state.update(status="strategy_complete")
            
            # Phase 3: Content Generation
            logger.info("═" * 60)
            logger.info("PHASE 3: CONTENT GENERATION")
            logger.info("═" * 60)
            content = await self.content_engine.run(research, strategy)
            self.state.save_content(content)
            self.state.update(status="content_complete")
            
            # Phase 4: Verification
            logger.info("═" * 60)
            logger.info("PHASE 4: SELF-VERIFICATION")
            logger.info("═" * 60)
            verification = await self.verification_engine.run(research, strategy, content)
            self.state.save_verification(verification)
            self.state.update(status="verification_complete")
            
            # Finalize
            self.state.update(status="completed")
            self.state.save_summary()
            
            logger.info("═" * 60)
            logger.info("✅ PIPELINE COMPLETE")
            logger.info("═" * 60)
            logger.info(f"📁 Output directory: {self.state.output_dir}")
            
            return {
                "session_id": self.state.session_id,
                "status": "success",
                "output_dir": str(self.state.output_dir),
                "research": research,
                "strategy": strategy,
                "content": content,
                "verification": verification,
                "errors": self.state.state.get("errors", [])
            }
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            self.state.update(status="failed")
            self.state.add_error(str(e))
            self.state.save_summary()
            raise
    
    async def run_research_only(self, business_url: str) -> ResearchResult:
        """Run only the research phase."""
        return await self.research_engine.run(business_url)
    
    async def run_strategy_only(self, research: ResearchResult) -> StrategyResult:
        """Run only the strategy phase."""
        return await self.strategy_engine.run(research)
    
    async def run_content_only(
        self,
        research: ResearchResult,
        strategy: StrategyResult
    ) -> ContentPackage:
        """Run only the content generation phase."""
        return await self.content_engine.run(research, strategy)
    
    async def run_verification_only(
        self,
        research: ResearchResult,
        strategy: StrategyResult,
        content: ContentPackage
    ) -> PipelineVerificationReport:
        """Run only the verification phase."""
        return await self.verification_engine.run(research, strategy, content)
    
    async def close(self):
        """Cleanup resources."""
        await self.llm.close()
        await self.search.close()
        await self.scraper.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
