"""Prompt templates for all phases."""

# ═══════════════════════════════════════════════════════════════
# PHASE 1: RESEARCH & DISCOVERY
# ═══════════════════════════════════════════════════════════════

RESEARCH_SYSTEM_PROMPT = """You are an elite OSINT market research analyst. Your job is to deeply understand a business from public information.
You must be thorough, evidence-based, and structured. Separate confirmed evidence from inference, avoid generic guesses, and cite source URLs for important claims.
Output must be valid JSON matching the expected schema exactly."""

RESEARCH_USER_PROMPT = """Analyze the following business information and produce a comprehensive research report.

BUSINESS URL: {url}

SCRAPED CONTENT:
{scraped_content}

SEARCH RESULTS:
{search_results}

Your task:
1. Extract the complete business profile (name, tagline, description, industry, niche, products, value proposition)
2. Identify 2-3 detailed buyer personas with demographics, pain points, goals, and preferred channels
3. Analyze brand voice from any available content (tone, style, keywords, phrases to avoid)
4. Use Google Maps/local, reviews, public social profiles, directories, and search evidence when present
5. Identify 2-3 key competitors and how this business differentiates
6. Extract 3-5 real content examples for few-shot learning
7. Provide evidence (URLs, quotes) for all claims
8. Give a confidence score (0.0-1.0) and summary that clearly states uncertainty

CRITICAL: Output MUST be a single valid JSON object with this exact structure:
{{
  "business": {{
    "name": "Company Name",
    "tagline": "One-liner description",
    "description": "Detailed paragraph about what they do",
    "industry": "Industry name",
    "niche": "Specific niche",
    "products": ["Product 1", "Product 2"],
    "value_proposition": "What makes them unique",
    "target_market": "Who they serve",
    "founded": "Year if known",
    "size": "Company size if known"
  }},
  "audience": [
    {{
      "persona": "Persona name",
      "demographics": "Age, location, industry",
      "pain_points": ["Pain 1", "Pain 2"],
      "goals": ["Goal 1"],
      "channels": ["LinkedIn", "Instagram"]
    }}
  ],
  "brand_voice": {{
    "tone": "e.g. Professional, Playful, Empowering",
    "style": "e.g. Concise, Storytelling, Direct",
    "keywords": ["word1", "word2"],
    "avoid": ["word1", "word2"],
    "examples": ["Example sentence 1", "Example sentence 2"]
  }},
  "competitors": [
    {{
      "name": "Competitor Name",
      "url": "https://competitor.com",
      "differentiator": "How target biz differs"
    }}
  ],
  "content_examples": ["Example post 1", "Example post 2"],
  "evidence": {{
    "source_urls": ["https://source1.com"],
    "quotes": ["Quote from source"],
    "search_queries_used": ["query 1"]
  }},
  "confidence_score": 0.85,
  "summary": "Executive summary paragraph"
}}

DO NOT output markdown code blocks. DO NOT output explanatory text. Output raw JSON ONLY."""

# ═══════════════════════════════════════════════════════════════
# PHASE 2: STRATEGY & PLANNING
# ═══════════════════════════════════════════════════════════════

STRATEGY_SYSTEM_PROMPT = """You are a Chief Content Strategist with 15 years of experience. You create data-driven content strategies that actually work.
Your strategies are specific, actionable, and always tied to business objectives.
Output must be valid JSON matching the expected schema exactly."""

STRATEGY_USER_PROMPT = """Based on the following research, create a complete content strategy.

RESEARCH SUMMARY:
{research_summary}

BUSINESS PROFILE:
{business_profile}

AUDIENCE PERSONAS:
{audience}

BRAND VOICE:
{brand_voice}

Your task:
1. Define 3-5 content pillars with descriptions and topic examples
2. Recommend 2-4 distribution channels with strategic rationale
3. Build a {calendar_days}-day content calendar with {posts_per_week} posts per week
4. Each calendar item must include: date, time, channel, pillar, topic, format, CTA, objective, target persona
5. Provide overall strategy summary and rationale tied to the research findings

Consider:
- Audience personas' preferred channels and pain points
- Brand voice and content examples
- Realistic posting cadence for a small business
- Mix of educational, promotional, and engagement content

CRITICAL: Output MUST be a single valid JSON object with this exact structure:
{{
  "pillars": [
    {{
      "name": "Pillar Name",
      "description": "What this pillar covers",
      "percentage": 40,
      "topics": ["Topic 1", "Topic 2"]
    }}
  ],
  "channels": [
    {{
      "channel": "LinkedIn",
      "purpose": "Why this channel",
      "audience_fit": "How audience uses it",
      "content_types": ["Posts", "Carousels"],
      "optimal_times": ["09:00", "14:00"],
      "frequency": "3x per week"
    }}
  ],
  "calendar": [
    {{
      "date": "2026-04-26",
      "time": "09:00",
      "channel": "LinkedIn",
      "pillar": "Pillar Name",
      "topic": "Specific topic",
      "format": "single",
      "cta": "Call to action text",
      "objective": "awareness",
      "target_persona": "Persona name"
    }}
  ],
  "overall_strategy": "Summary of strategy",
  "rationale": "Why this strategy was chosen"
}}

DO NOT output markdown code blocks. DO NOT output explanatory text. Output raw JSON ONLY."""

# ═══════════════════════════════════════════════════════════════
# PHASE 3: CONTENT GENERATION
# ═══════════════════════════════════════════════════════════════

CONTENT_SYSTEM_PROMPT = """You are a senior brand copywriter and content strategist.
You write crisp, specific, evidence-aware marketing content that feels human and useful.
You avoid generic AI filler, vague hype, unsupported claims, and inflated language.
You adapt to the channel while preserving the brand voice and making the final output display-ready.

Format every answer as clean Markdown that can be shown directly in a content card."""

CONTENT_USER_PROMPT = """Write marketing content based on the following brief.

BUSINESS: {business_name}
TAGLINE: {tagline}
VALUE PROPOSITION: {value_proposition}

BRAND VOICE:
- Tone: {tone}
- Style: {style}
- Keywords: {keywords}
- Avoid: {avoid}
- Examples: {examples}

TARGET PERSONA: {persona}
PAIN POINTS: {pain_points}

CONTENT BRIEF:
- Channel: {channel}
- Format: {format}
- Topic: {topic}
- Objective: {objective}
- CTA: {cta}

OUTPUT FORMAT:
Write display-ready Markdown with this structure:

## Hook
One or two sharp opening lines. No generic questions like "Are you ready?"

## Post
The final post body. Use short paragraphs or bullets where useful. Keep it specific to the business, audience, and topic.

## Proof Angle
One concise line tying the post to a real business signal, customer pain, offer, location, social proof, or research-backed insight. Do not invent facts.

## CTA
Use this CTA naturally: {cta}

## Hashtags
3-5 relevant hashtags, only if appropriate for {channel}.

## Image Idea
One practical visual direction for a designer or image model.

QUALITY BAR:
- Match the brand voice exactly. Use examples as style references, not content to copy.
- Make the first two lines strong enough to stand alone in a feed.
- Prefer concrete nouns and verbs over buzzwords.
- Avoid unsupported metrics, fake testimonials, and claims not implied by the research.
- Keep it concise for the channel. Do not ramble.
- Output only the Markdown content. No commentary before or after."""

# ═══════════════════════════════════════════════════════════════
# PHASE 4: SELF-VERIFICATION
# ═══════════════════════════════════════════════════════════════

VERIFICATION_SYSTEM_PROMPT = """You are a ruthless content editor and fact-checker.
Your job is to verify marketing content against brand standards, factual accuracy, and channel requirements.
You are extremely critical — most first drafts fail.
You provide specific, actionable feedback with scores.
Output must be valid JSON."""

BRAND_ALIGNMENT_PROMPT = """Check if the following content matches the brand voice.

BRAND VOICE:
- Tone: {tone}
- Style: {style}
- Keywords: {keywords}
- Avoid: {avoid}
- Examples: {examples}

CONTENT TO CHECK:
{content}

Evaluate:
1. Does the tone match? (score 0-1)
2. Does it use appropriate keywords?
3. Does it avoid forbidden words/phrases?
4. Does it sound like it came from this brand?
5. Is the style consistent with examples?

Output JSON with: status (PASS/FAIL/WARNING), score (0-1), issues (list), suggestions (list)"""

FACT_CHECK_PROMPT = """Fact-check the following content against the research data.

RESEARCH DATA:
{business_facts}

CONTENT TO CHECK:
{content}

Evaluate:
1. Are all factual claims supported by research?
2. Are there any hallucinations or unsupported claims?
3. Are statistics/numbers accurate?
4. Is the business description accurate?

Output JSON with: status (PASS/FAIL/WARNING), score (0-1), issues (list), suggestions (list)"""

FORMAT_CHECK_PROMPT = """Check if the content follows channel format requirements.

CHANNEL: {channel}
FORMAT: {format}
REQUIREMENTS:
{requirements}

CONTENT TO CHECK:
{content}

Evaluate:
1. Character count within limits?
2. Proper use of hashtags?
3. Format matches expectation (thread, carousel, single)?
4. CTA present and appropriate?
5. Visual suggestions included?

Output JSON with: status (PASS/FAIL/WARNING), score (0-1), issues (list), suggestions (list)"""

QUALITY_CHECK_PROMPT = """Evaluate the overall quality of this content.

CONTENT:
{content}

Evaluate:
1. Grammar and spelling (score 0-1)
2. Clarity and readability (score 0-1)
3. Hook strength (first 2 lines) (score 0-1)
4. CTA effectiveness (score 0-1)
5. Overall engagement potential (score 0-1)

Output JSON with: status (PASS/FAIL/WARNING), score (0-1, average of above), issues (list), suggestions (list)"""

REFINE_PROMPT = """You are rewriting content based on editor feedback.

ORIGINAL CONTENT:
{original_content}

EDITOR FEEDBACK:
{feedback}

BRAND VOICE:
- Tone: {tone}
- Style: {style}
- Keywords: {keywords}

Your task:
1. Address ALL issues raised in the feedback
2. Maintain the brand voice
3. Keep the core message and CTA
4. Make it better, not just different

Output the revised content only."""

# ═══════════════════════════════════════════════════════════════
# CHANNEL REQUIREMENTS REFERENCE
# ═══════════════════════════════════════════════════════════════

CHANNEL_REQUIREMENTS = {
    "LinkedIn": {
        "char_limit": 3000,
        "ideal_length": "1300-1500 chars for single post",
        "hashtags": "3-5 hashtags",
        "best_practices": [
            "Professional but personable tone",
            "Line breaks for readability",
            "Strong hook in first 2 lines",
            "Clear CTA at end",
            "Tag relevant people/companies"
        ]
    },
    "X": {
        "char_limit": 280,
        "ideal_length": "Under 280 chars per tweet",
        "hashtags": "1-2 hashtags max",
        "best_practices": [
            "Punchy and direct",
            "Thread for longer content",
            "Engage with questions",
            "Use emojis sparingly"
        ]
    },
    "Twitter": {
        "char_limit": 280,
        "ideal_length": "Under 280 chars per tweet",
        "hashtags": "1-2 hashtags max",
        "best_practices": [
            "Punchy and direct",
            "Thread for longer content",
            "Engage with questions",
            "Use emojis sparingly"
        ]
    },
    "Instagram": {
        "char_limit": 2200,
        "ideal_length": "Short caption + engaging visual",
        "hashtags": "5-10 hashtags",
        "best_practices": [
            "Visual-first approach",
            "Emojis welcome",
            "Storytelling captions",
            "Strong visual CTA"
        ]
    },
    "Blog": {
        "char_limit": "Unlimited",
        "ideal_length": "800-2000 words",
        "hashtags": "Not applicable",
        "best_practices": [
            "SEO-optimized headers",
            "Scannable structure",
            "Internal/external links",
            "Meta description",
            "Clear conclusion with CTA"
        ]
    }
}
