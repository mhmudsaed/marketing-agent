"""Database models and session management."""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, JSON, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from config.settings import settings

Base = declarative_base()

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    business_url = Column(String(500), nullable=False)
    model_mode = Column(String(50), default="offline")
    model_name = Column(String(255))
    user_goal = Column(Text)
    extra_context = Column(Text)
    status = Column(String(50), default="draft")  # draft, researching, strategizing, generating, verifying, ready, published
    progress = Column(Integer, default=0)  # 0-100
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    research = relationship("Research", back_populates="campaign", uselist=False)
    strategy = relationship("Strategy", back_populates="campaign", uselist=False)
    posts = relationship("Post", back_populates="campaign", order_by="Post.date")

class Research(Base):
    __tablename__ = "research"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), unique=True)
    
    business_name = Column(String(255))
    tagline = Column(String(500))
    description = Column(Text)
    industry = Column(String(100))
    niche = Column(String(100))
    products = Column(JSON, default=list)
    value_proposition = Column(Text)
    target_market = Column(Text)
    
    brand_tone = Column(String(100))
    brand_style = Column(String(100))
    brand_keywords = Column(JSON, default=list)
    brand_avoid = Column(JSON, default=list)
    brand_examples = Column(JSON, default=list)
    
    audience = Column(JSON, default=list)
    competitors = Column(JSON, default=list)
    content_examples = Column(JSON, default=list)
    
    confidence_score = Column(Float, default=0.0)
    summary = Column(Text)
    evidence_urls = Column(JSON, default=list)
    locations = Column(JSON, default=list)
    social_profiles = Column(JSON, default=list)
    reviews_summary = Column(JSON, default=dict)
    osint_sources = Column(JSON, default=list)
    search_tool_coverage = Column(JSON, default=dict)
    competitor_evidence = Column(JSON, default=list)
    research_depth = Column(String(50), default="standard")
    
    campaign = relationship("Campaign", back_populates="research")

class Strategy(Base):
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), unique=True)
    
    pillars = Column(JSON, default=list)
    channels = Column(JSON, default=list)
    overall_strategy = Column(Text)
    rationale = Column(Text)
    
    campaign = relationship("Campaign", back_populates="strategy")

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    
    # Content
    title = Column(String(500))
    headline = Column(Text)
    body = Column(Text)
    cta = Column(Text)
    hashtags = Column(JSON, default=list)
    
    # Scheduling
    date = Column(String(20))
    time = Column(String(10))
    timezone = Column(String(50), default="UTC")
    
    # Channel & format
    channel = Column(String(50))
    format = Column(String(50))
    pillar = Column(String(100))
    topic = Column(String(500))
    objective = Column(String(100))
    target_persona = Column(String(100))
    
    # Media
    image_prompt = Column(Text)
    image_url = Column(String(500))
    
    # Status
    status = Column(String(50), default="draft")  # draft, approved, scheduled, published, rejected
    
    # Verification
    verification_score = Column(Float, default=0.0)
    verification_status = Column(String(50))
    verification_details = Column(JSON, default=dict)
    
    # Publishing
    published_at = Column(DateTime)
    publish_error = Column(Text)
    platform_post_id = Column(String(255))
    
    # Metadata
    word_count = Column(Integer, default=0)
    char_count = Column(Integer, default=0)
    reading_time = Column(String(20))
    model_used = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    campaign = relationship("Campaign", back_populates="posts")

class BrandVoiceTemplate(Base):
    __tablename__ = "brand_voice_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    tone = Column(String(100))
    style = Column(String(100))
    keywords = Column(JSON, default=list)
    avoid = Column(JSON, default=list)
    examples = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

class PublishingAccount(Base):
    __tablename__ = "publishing_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False)  # linkedin, x, instagram, facebook
    account_name = Column(String(255))
    access_token = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Database setup
DATABASE_URL = f"sqlite:///{settings.OUTPUT_DIR}/app.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_campaign_columns()
    _migrate_research_columns()

def _migrate_campaign_columns():
    """Add chat-onboarding metadata columns for existing SQLite databases."""
    inspector = inspect(engine)
    if "campaigns" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("campaigns")}
    additions = {
        "model_mode": "VARCHAR(50) DEFAULT 'offline'",
        "model_name": "VARCHAR(255)",
        "user_goal": "TEXT",
        "extra_context": "TEXT",
    }
    with engine.begin() as conn:
        for column, ddl in additions.items():
            if column not in existing:
                conn.execute(text(f"ALTER TABLE campaigns ADD COLUMN {column} {ddl}"))

def _migrate_research_columns():
    """Add newly introduced JSON columns for existing SQLite databases."""
    inspector = inspect(engine)
    if "research" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("research")}
    additions = {
        "locations": "JSON DEFAULT '[]'",
        "social_profiles": "JSON DEFAULT '[]'",
        "reviews_summary": "JSON DEFAULT '{}'",
        "osint_sources": "JSON DEFAULT '[]'",
        "search_tool_coverage": "JSON DEFAULT '{}'",
        "competitor_evidence": "JSON DEFAULT '[]'",
        "research_depth": "VARCHAR(50) DEFAULT 'standard'",
    }
    with engine.begin() as conn:
        for column, ddl in additions.items():
            if column not in existing:
                conn.execute(text(f"ALTER TABLE research ADD COLUMN {column} {ddl}"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
