"""Pipeline state management with persistence."""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from models.research import ResearchResult
from models.strategy import StrategyResult
from models.content import ContentPackage
from models.verification import PipelineVerificationReport
from config.settings import settings
from utils.logger import logger

class PipelineStateManager:
    """Manages pipeline state with JSON persistence."""
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.started_at = datetime.utcnow().isoformat()
        self.output_dir = settings.OUTPUT_DIR / self.session_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.state = {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "status": "initialized",
            "business_url": None,
            "errors": []
        }
        
        logger.info(f"Pipeline session: {self.session_id}")
    
    def update(self, **kwargs):
        """Update state fields."""
        self.state.update(kwargs)
        self._persist_state()
    
    def add_error(self, error: str):
        """Record non-fatal error."""
        self.state["errors"].append({
            "time": datetime.utcnow().isoformat(),
            "error": error
        })
        self._persist_state()
    
    def save_research(self, research: ResearchResult):
        """Save research output."""
        path = self.output_dir / "research.json"
        with open(path, "w") as f:
            json.dump(research.model_dump(), f, indent=2, default=str)
        logger.info(f"💾 Research saved: {path}")
    
    def save_strategy(self, strategy: StrategyResult):
        """Save strategy output."""
        path = self.output_dir / "strategy.json"
        with open(path, "w") as f:
            json.dump(strategy.model_dump(), f, indent=2, default=str)
        logger.info(f"💾 Strategy saved: {path}")
    
    def save_content(self, content: ContentPackage):
        """Save content output."""
        path = self.output_dir / "content.json"
        with open(path, "w") as f:
            json.dump(content.model_dump(), f, indent=2, default=str)
        logger.info(f"💾 Content saved: {path}")
        
        # Also save individual posts as markdown
        posts_dir = self.output_dir / "posts"
        posts_dir.mkdir(exist_ok=True)
        
        for idx, post in enumerate(content.contents):
            md_path = posts_dir / f"post_{idx:02d}_{post.channel.lower()}.md"
            with open(md_path, "w") as f:
                f.write(self._post_to_markdown(post, idx))
    
    def save_verification(self, verification: PipelineVerificationReport):
        """Save verification output."""
        path = self.output_dir / "verification.json"
        with open(path, "w") as f:
            json.dump(verification.model_dump(), f, indent=2, default=str)
        logger.info(f"💾 Verification saved: {path}")
    
    def save_summary(self):
        """Save final pipeline summary."""
        path = self.output_dir / "summary.json"
        self.state["completed_at"] = datetime.utcnow().isoformat()
        with open(path, "w") as f:
            json.dump(self.state, f, indent=2, default=str)
    
    def _persist_state(self):
        """Persist current state to disk."""
        path = self.output_dir / "state.json"
        with open(path, "w") as f:
            json.dump(self.state, f, indent=2, default=str)
    
    def _post_to_markdown(self, post, idx: int) -> str:
        """Convert post to markdown."""
        md = f"""# Post {idx+1}: {post.topic}

## Metadata
- **Channel:** {post.channel}
- **Format:** {post.format}
- **Model:** {post.model_used}
- **Generation Time:** {post.generation_time_ms}ms
- **Words:** {post.word_count} | **Chars:** {post.char_count}
- **Reading Time:** {post.reading_time or 'N/A'}

## Headline / Hook
{post.headline}

## Body
{post.body}

## CTA
{post.cta}

## Hashtags
{', '.join(post.hashtags) if post.hashtags else 'None'}

## Image Suggestion
**Style:** {post.suggested_image_style or 'N/A'}

**Prompt:** {post.image_prompt or 'N/A'}

---

## Variants
"""
        for i, variant in enumerate(post.variants):
            md += f"\n### Variant {i+1}\n{variant}\n"
        
        return md
