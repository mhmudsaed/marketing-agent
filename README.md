# Marketing Content Pipeline Agent

> **Enterprise-grade AI agent that builds complete marketing content pipelines — from research to published content.**

Built for [The Agent Lab Hackathon](https://theagentlab.dev/) but designed for production use.

---

## What It Does

This agent autonomously:

1. **Researches** any business from public sources (website, search, social)
2. **Strategizes** content pillars, channels, and a posting calendar
3. **Generates** channel-optimized marketing content with brand voice matching
4. **Verifies** its own output (brand alignment, facts, format, quality) and auto-refines

**One command. Full campaign. Zero manual work.**

---

## Architecture

```
Business URL
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: Research & Discovery                                   │
│ • Website scraping + search intelligence                        │
│ • Business profiling, audience personas, brand voice extraction │
│ • Competitor analysis                                           │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: Strategy & Planning                                    │
│ • Content pillars & themes                                      │
│ • Channel strategy with rationale                               │
│ • Data-driven content calendar                                  │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: Content Generation                                     │
│ • Few-shot brand voice matching                                 │
│ • Channel-optimized formats (LinkedIn, X, IG, Blog)             │
│ • Multiple variants per post                                    │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 4: Self-Verification & Auto-Refinement                    │
│ • Brand alignment check (embedding similarity)                  │
│ • Fact-checking against research data                           │
│ • Format compliance per channel                                 │
│ • Quality scoring (readability, hook strength)                  │
│ • Auto-refinement loop: FAIL → Rewrite → Re-check               │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
📁 Complete content package saved to disk
   • research.json
   • strategy.json
   • content.json
   • verification.json
   • Individual .md posts
```

---

## Project Structure

```
marketing-agent/
├── main.py                  # CLI entry point
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
│
├── config/
│   └── settings.py          # Centralized configuration
│
├── models/                  # Pydantic data models
│   ├── research.py          # Phase 1 models
│   ├── strategy.py          # Phase 2 models
│   ├── content.py           # Phase 3 models
│   └── verification.py      # Phase 4 models
│
├── clients/                 # External API clients
│   ├── openrouter.py        # LLM client (OpenRouter)
│   ├── tavily.py            # AI search client
│   └── scraper.py           # Web scraping (HTTP + Firecrawl)
│
├── phases/                  # Core business logic
│   ├── research.py          # Research engine
│   ├── strategy.py          # Strategy engine
│   ├── content.py           # Content generation engine
│   └── verification.py      # Self-verification engine
│
├── core/                    # Orchestration
│   ├── state.py             # State management & persistence
│   └── pipeline.py          # Pipeline orchestrator
│
├── utils/                   # Utilities
│   ├── logger.py            # Structured logging
│   ├── validators.py        # Content validation
│   └── prompts.py           # LLM prompt templates
│
└── outputs/                 # Generated at runtime
    └── {session_id}/
        ├── research.json
        ├── strategy.json
        ├── content.json
        ├── verification.json
        ├── state.json
        ├── summary.json
        └── posts/
            ├── post_00_linkedin.md
            ├── post_01_x.md
            └── ...
```

---

## Quick Start

### 1. Install Dependencies

```bash
cd marketing-agent
pip install -r requirements.txt
```

### 2. Configure API Keys

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
# Edit .env with your keys
```

### 3. Run the Agent

```bash
# Full pipeline
python main.py --url https://example.com

# Research only
python main.py --url https://example.com --research-only

# Use a specific model via OpenRouter
python main.py --url https://example.com --model anthropic/claude-3-opus
```

---

## API Keys Required

| Service | Purpose | Get Key At |
|---------|---------|------------|
| **OpenRouter** | LLM access (Claude, GPT, etc.) | [openrouter.ai/keys](https://openrouter.ai/keys) |
| **Tavily** | AI-optimized web search | [tavily.com](https://tavily.com) |
| **Firecrawl** | Advanced web scraping (optional) | [firecrawl.dev](https://firecrawl.dev) |

### Cost Estimates (per run)

| Service | Estimated Cost | Notes |
|---------|---------------|-------|
| OpenRouter | $0.10 - $0.50 | Depends on model and content volume |
| Tavily | Free tier: 1,000/mo | Pro: $0.025/search |
| Firecrawl | Free tier available | Pro plans for scale |

---

## Configuration

All configuration is via environment variables (see `.env.example`):

```env
# OpenRouter (REQUIRED)
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# Tavily (REQUIRED)
TAVILY_API_KEY=tvly-...

# Firecrawl (OPTIONAL)
FIRECRAWL_API_KEY=fc-...

# Pipeline Settings
MAX_VERIFICATION_RETRIES=3
MAX_CONTENT_VARIANTS=3
DEFAULT_CALENDAR_DAYS=14
```

---

## Hackathon Judging Alignment

This agent is architected to maximize scores on every criterion:

| Criterion | Weight | How We Score |
|-----------|--------|--------------|
| **Content Quality** | 25% | Few-shot prompting with real brand examples; channel-optimized formats; scroll-stopping hooks |
| **Self-Verification** | 25% | 4-check verification loop (brand, facts, format, quality) with auto-refinement up to 3 iterations |
| **Research Depth** | 20% | Multi-page scraping + AI search + competitor analysis + structured evidence |
| **Pipeline Completeness** | 20% | True end-to-end: research → strategy → calendar → content → verification |
| **Technical Implementation** | 5% | Clean architecture, Pydantic models, retry logic, structured logging |
| **Presentation** | 5% | Rich CLI output, saved markdown posts, quantified verification scores |
| **Autonomy (Bonus)** | Extra | Single command runs entire pipeline; no human intervention between phases |
| **Long-Running (Bonus)** | Extra | Async architecture, timeout handling, graceful degradation |

---

## Enterprise Features

- **Structured Logging:** All operations logged with timestamps and context
- **State Persistence:** Every phase output saved to JSON for audit trails
- **Retry Logic:** Exponential backoff on all external API calls
- **Graceful Degradation:** If search fails, scraper continues; if LLM fails, fallbacks activate
- **Modular Design:** Each phase is independently runnable for testing/debugging
- **Pydantic Validation:** All inputs/outputs are typed and validated
- **Async Architecture:** Concurrent operations where possible for speed

---

## Demo Script (For Hackathon Presentation)

```bash
# 1. Show the agent running on a real business
python main.py --url https://www.bldr.space

# 2. Show research output
cat outputs/xxxxxx/research.json | jq '.business'

# 3. Show generated content
cat outputs/xxxxxx/posts/post_00_linkedin.md

# 4. Show verification scores
cat outputs/xxxxxx/verification.json | jq '.average_score'
```

---

## License

MIT — Built with rage and caffeine for The Agent Lab 2026.

---

**Ready to launch. 🔥**
