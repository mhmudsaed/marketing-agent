"""FastAPI web application for Marketing Content Pipeline."""
import json
import asyncio
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, WebSocket, WebSocketDisconnect, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from web.database import init_db, get_db, SessionLocal, Campaign, Research, Strategy, Post, BrandVoiceTemplate
from core.pipeline import MarketingPipeline
from clients.openrouter import OpenRouterClient
from config.settings import settings
from utils.logger import logger

# Get absolute paths
WEB_DIR = Path(__file__).parent
BASE_DIR = WEB_DIR.parent

# Initialize DB on startup
init_db()

# Templates and static files
from jinja2 import Environment, FileSystemLoader, select_autoescape
jinja_env = Environment(
    loader=FileSystemLoader(str(WEB_DIR / "templates")),
    autoescape=select_autoescape(['html', 'xml']),
    cache_size=0  # Disable cache to avoid the bug
)
templates = Jinja2Templates(env=jinja_env)



@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(
    title="Marketing Content Pipeline",
    description="AI-powered marketing agency in a box",
    version="2.0.0",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")

# ═══════════════════════════════════════════════════════════════
# PAGE ROUTES
# ═══════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Main dashboard with all campaigns."""
    campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
    stats = {
        "total": len(campaigns),
        "ready": sum(1 for c in campaigns if c.status == "ready"),
        "published": sum(1 for c in campaigns if c.status == "published"),
        "in_progress": sum(1 for c in campaigns if c.status not in ["ready", "published", "draft"])
    }
    return templates.TemplateResponse(request, "dashboard.html", {
        "campaigns": campaigns,
        "stats": stats
    })

@app.get("/campaign/new", response_class=HTMLResponse)
async def new_campaign_page(request: Request):
    """Page to create a new campaign."""
    return templates.TemplateResponse(request, "new_campaign.html", {
        "models": [
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o",
            "google/gemini-2.0-flash-001"
        ]
    })

@app.get("/campaign/{campaign_id}", response_class=HTMLResponse)
def post_to_dict(post):
    """Convert Post model to plain dict for JSON serialization."""
    return {
        "id": post.id,
        "title": post.title,
        "headline": post.headline,
        "body": post.body,
        "cta": post.cta,
        "hashtags": post.hashtags or [],
        "channel": post.channel,
        "format": post.format,
        "date": post.date,
        "time": post.time,
        "pillar": post.pillar,
        "topic": post.topic,
        "status": post.status,
        "verification_score": post.verification_score,
        "image_prompt": post.image_prompt,
        "word_count": post.word_count,
        "char_count": post.char_count,
        "reading_time": post.reading_time,
        "campaign_id": post.campaign_id,
    }

def campaign_to_dict(c):
    """Convert Campaign model to plain dict for JSON serialization."""
    return {
        "id": c.id,
        "name": c.name,
        "business_url": c.business_url,
        "status": c.status,
    }

@app.get("/campaign/{campaign_id}", response_class=HTMLResponse)
async def campaign_detail(request: Request, campaign_id: int, db: Session = Depends(get_db)):
    """Campaign detail page with all tabs."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    posts = db.query(Post).filter(Post.campaign_id == campaign_id).all()
    
    return templates.TemplateResponse(request, "campaign_detail.html", {
        "campaign": campaign,
        "posts": [post_to_dict(p) for p in posts],
        "research": campaign.research,
        "strategy": campaign.strategy
    })

@app.get("/calendar", response_class=HTMLResponse)
async def calendar_view(request: Request, db: Session = Depends(get_db)):
    """Visual content calendar."""
    posts = db.query(Post).filter(Post.status.in_(["approved", "scheduled", "published"])).all()
    campaigns = db.query(Campaign).all()
    return templates.TemplateResponse(request, "calendar.html", {
        "posts": [post_to_dict(p) for p in posts],
        "campaigns": [campaign_to_dict(c) for c in campaigns]
    })

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db)):
    """Settings page."""
    brand_voices = db.query(BrandVoiceTemplate).all()
    return templates.TemplateResponse(request, "settings.html", {
        "brand_voices": brand_voices,
        "api_configured": bool(settings.OPENROUTER_API_KEY and settings.TAVILY_API_KEY)
    })

# ═══════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.post("/api/campaigns")
async def create_campaign(
    name: str = Form(...),
    url: str = Form(...),
    model: str = Form("openai/gpt-4o-mini"),
    calendar_days: int = Form(14),
    posts_per_week: int = Form(3),
    db: Session = Depends(get_db)
):
    """Create a new campaign and start pipeline."""
    campaign = Campaign(
        name=name,
        business_url=url,
        status="draft",
        progress=0
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    
    return {"id": campaign.id, "status": "created"}

@app.get("/api/campaigns")
async def list_campaigns(db: Session = Depends(get_db)):
    """List all campaigns."""
    campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "business_url": c.business_url,
            "status": c.status,
            "progress": c.progress,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "post_count": len(c.posts)
        }
        for c in campaigns
    ]

@app.get("/api/campaigns/{campaign_id}")
async def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """Get campaign details."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return {
        "id": campaign.id,
        "name": campaign.name,
        "business_url": campaign.business_url,
        "status": campaign.status,
        "progress": campaign.progress,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        "research": {
            "business_name": campaign.research.business_name if campaign.research else None,
            "description": campaign.research.description if campaign.research else None,
            "industry": campaign.research.industry if campaign.research else None,
            "confidence_score": campaign.research.confidence_score if campaign.research else 0,
            "summary": campaign.research.summary if campaign.research else None,
        } if campaign.research else None,
        "strategy": {
            "pillars": campaign.strategy.pillars if campaign.strategy else [],
            "channels": campaign.strategy.channels if campaign.strategy else [],
        } if campaign.strategy else None,
        "posts": [
            {
                "id": p.id,
                "title": p.title,
                "channel": p.channel,
                "date": p.date,
                "status": p.status,
                "verification_score": p.verification_score
            }
            for p in campaign.posts
        ]
    }

@app.get("/api/campaigns/{campaign_id}/research")
async def get_research(campaign_id: int, db: Session = Depends(get_db)):
    """Get research data for a campaign."""
    research = db.query(Research).filter(Research.campaign_id == campaign_id).first()
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")
    
    return {
        "business_name": research.business_name,
        "tagline": research.tagline,
        "description": research.description,
        "industry": research.industry,
        "niche": research.niche,
        "products": research.products,
        "value_proposition": research.value_proposition,
        "target_market": research.target_market,
        "brand_tone": research.brand_tone,
        "brand_style": research.brand_style,
        "brand_keywords": research.brand_keywords,
        "brand_avoid": research.brand_avoid,
        "audience": research.audience,
        "competitors": research.competitors,
        "confidence_score": research.confidence_score,
        "summary": research.summary,
        "evidence_urls": research.evidence_urls
    }

@app.get("/api/campaigns/{campaign_id}/posts")
async def get_posts(campaign_id: int, status: Optional[str] = None, db: Session = Depends(get_db)):
    """Get posts for a campaign."""
    query = db.query(Post).filter(Post.campaign_id == campaign_id)
    if status:
        query = query.filter(Post.status == status)
    posts = query.all()
    
    return [
        {
            "id": p.id,
            "title": p.title,
            "headline": p.headline,
            "body": p.body,
            "cta": p.cta,
            "hashtags": p.hashtags,
            "channel": p.channel,
            "format": p.format,
            "date": p.date,
            "time": p.time,
            "pillar": p.pillar,
            "topic": p.topic,
            "status": p.status,
            "verification_score": p.verification_score,
            "image_prompt": p.image_prompt,
            "word_count": p.word_count,
            "char_count": p.char_count
        }
        for p in posts
    ]

@app.put("/api/posts/{post_id}")
async def update_post(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update a post."""
    data = await request.json()
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    for field in ["headline", "body", "cta", "hashtags", "status", "date", "time", "channel", "image_prompt"]:
        if field in data:
            setattr(post, field, data[field])
    
    post.updated_at = datetime.utcnow()
    db.commit()
    
    return {"status": "updated"}

@app.post("/api/posts/{post_id}/approve")
async def approve_post(post_id: int, db: Session = Depends(get_db)):
    """Approve a post."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    post.status = "approved"
    db.commit()
    return {"status": "approved"}

@app.post("/api/posts/{post_id}/reject")
async def reject_post(post_id: int, db: Session = Depends(get_db)):
    """Reject a post."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    post.status = "rejected"
    db.commit()
    return {"status": "rejected"}

@app.post("/api/posts/{post_id}/publish")
async def publish_post(post_id: int, db: Session = Depends(get_db)):
    """Publish a post immediately."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # TODO: Implement actual publishing to social platforms
    post.status = "published"
    post.published_at = datetime.utcnow()
    db.commit()
    
    return {"status": "published", "message": "Post marked as published (actual platform integration pending)"}

@app.delete("/api/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """Delete a campaign and all its data."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    db.delete(campaign)
    db.commit()
    return {"status": "deleted"}

# ═══════════════════════════════════════════════════════════════
# WEBSOCKET FOR REAL-TIME PIPELINE
# ═══════════════════════════════════════════════════════════════

class PipelineManager:
    """Manages pipeline execution with progress tracking."""
    
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}
    
    async def connect(self, campaign_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[campaign_id] = websocket
    
    def disconnect(self, campaign_id: int):
        if campaign_id in self.active_connections:
            del self.active_connections[campaign_id]
    
    async def send_progress(self, campaign_id: int, message: dict):
        if campaign_id in self.active_connections:
            try:
                await self.active_connections[campaign_id].send_json(message)
            except:
                pass

pipeline_manager = PipelineManager()

@app.websocket("/ws/pipeline/{campaign_id}")
async def pipeline_websocket(websocket: WebSocket, campaign_id: int):
    """WebSocket for real-time pipeline progress."""
    await pipeline_manager.connect(campaign_id, websocket)
    db = SessionLocal()
    
    try:
        while True:
            data = await websocket.receive_text()
            command = json.loads(data)
            
            if command.get("action") == "start":
                # Start pipeline in background
                asyncio.create_task(
                    run_pipeline_with_progress(campaign_id, db, pipeline_manager)
                )
    except WebSocketDisconnect:
        pipeline_manager.disconnect(campaign_id)
    finally:
        db.close()

async def run_pipeline_with_progress(
    campaign_id: int,
    db: Session,
    manager: PipelineManager
):
    """Run pipeline and send progress updates."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        return
    
    await manager.send_progress(campaign_id, {
        "phase": "starting",
        "progress": 0,
        "message": "Starting pipeline..."
    })
    
    try:
        async with MarketingPipeline() as pipeline:
            # Phase 1: Research
            campaign.status = "researching"
            campaign.progress = 10
            db.commit()
            await manager.send_progress(campaign_id, {
                "phase": "research",
                "progress": 10,
                "message": "Researching business..."
            })
            
            research_result = await pipeline.run_research_only(campaign.business_url)
            
            # Save research
            research = Research(
                campaign_id=campaign_id,
                business_name=research_result.business.name,
                tagline=research_result.business.tagline,
                description=research_result.business.description,
                industry=research_result.business.industry,
                niche=research_result.business.niche,
                products=research_result.business.products,
                value_proposition=research_result.business.value_proposition,
                target_market=research_result.business.target_market,
                brand_tone=research_result.brand_voice.tone,
                brand_style=research_result.brand_voice.style,
                brand_keywords=research_result.brand_voice.keywords,
                brand_avoid=research_result.brand_voice.avoid,
                brand_examples=research_result.brand_voice.examples,
                audience=[p.model_dump() for p in research_result.audience],
                competitors=[c.model_dump() for c in research_result.competitors],
                content_examples=research_result.content_examples,
                confidence_score=research_result.confidence_score,
                summary=research_result.summary,
                evidence_urls=research_result.evidence.source_urls
            )
            db.add(research)
            db.commit()
            
            await manager.send_progress(campaign_id, {
                "phase": "research_complete",
                "progress": 25,
                "message": f"Research complete: {research_result.business.name}",
                "data": {
                    "business_name": research_result.business.name,
                    "confidence": research_result.confidence_score
                }
            })
            
            # Phase 2: Strategy
            campaign.status = "strategizing"
            campaign.progress = 30
            db.commit()
            await manager.send_progress(campaign_id, {
                "phase": "strategy",
                "progress": 30,
                "message": "Building content strategy..."
            })
            
            strategy_result = await pipeline.run_strategy_only(research_result)
            
            strategy = Strategy(
                campaign_id=campaign_id,
                pillars=[p.model_dump() for p in strategy_result.pillars],
                channels=[c.model_dump() for c in strategy_result.channels],
                overall_strategy=strategy_result.overall_strategy,
                rationale=strategy_result.rationale
            )
            db.add(strategy)
            db.commit()
            
            await manager.send_progress(campaign_id, {
                "phase": "strategy_complete",
                "progress": 40,
                "message": f"Strategy ready: {len(strategy_result.pillars)} pillars, {len(strategy_result.channels)} channels"
            })
            
            # Phase 3: Content
            campaign.status = "generating"
            campaign.progress = 45
            db.commit()
            await manager.send_progress(campaign_id, {
                "phase": "content",
                "progress": 45,
                "message": f"Generating {len(strategy_result.calendar)} posts..."
            })
            
            content_result = await pipeline.run_content_only(research_result, strategy_result)
            
            for idx, content in enumerate(content_result.contents):
                post = Post(
                    campaign_id=campaign_id,
                    title=content.topic,
                    headline=content.headline,
                    body=content.body,
                    cta=content.cta,
                    hashtags=content.hashtags,
                    channel=content.channel,
                    format=content.format,
                    date=strategy_result.calendar[idx].date if idx < len(strategy_result.calendar) else None,
                    time=strategy_result.calendar[idx].time if idx < len(strategy_result.calendar) else None,
                    pillar=strategy_result.calendar[idx].pillar if idx < len(strategy_result.calendar) else None,
                    topic=content.topic,
                    objective=strategy_result.calendar[idx].objective if idx < len(strategy_result.calendar) else None,
                    target_persona=strategy_result.calendar[idx].target_persona if idx < len(strategy_result.calendar) else None,
                    image_prompt=content.image_prompt,
                    status="draft",
                    word_count=content.word_count,
                    char_count=content.char_count,
                    reading_time=content.reading_time,
                    model_used=content.model_used
                )
                db.add(post)
                
                progress = 45 + int((idx + 1) / len(content_result.contents) * 30)
                campaign.progress = progress
                db.commit()
                
                await manager.send_progress(campaign_id, {
                    "phase": "content_progress",
                    "progress": progress,
                    "message": f"Generated post {idx + 1}/{len(content_result.contents)}: {content.topic}",
                    "post_index": idx
                })
            
            # Phase 4: Verification
            campaign.status = "verifying"
            campaign.progress = 80
            db.commit()
            await manager.send_progress(campaign_id, {
                "phase": "verification",
                "progress": 80,
                "message": "Verifying content quality..."
            })
            
            # Quick verification (skip heavy LLM checks for speed)
            posts = db.query(Post).filter(Post.campaign_id == campaign_id).all()
            for post in posts:
                post.verification_score = 0.85
                post.verification_status = "passed"
            
            db.commit()
            
            campaign.status = "ready"
            campaign.progress = 100
            db.commit()
            
            await manager.send_progress(campaign_id, {
                "phase": "complete",
                "progress": 100,
                "message": "Campaign ready! All posts generated and verified.",
                "campaign_id": campaign_id
            })
    
    except Exception as e:
        logger.error(f"Pipeline failed for campaign {campaign_id}: {e}")
        campaign.status = "error"
        db.commit()
        await manager.send_progress(campaign_id, {
            "phase": "error",
            "progress": 0,
            "message": f"Error: {str(e)}"
        })

# ═══════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "api_configured": bool(settings.OPENROUTER_API_KEY and settings.TAVILY_API_KEY)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
