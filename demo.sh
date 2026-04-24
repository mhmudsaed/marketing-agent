#!/usr/bin/env bash
# Demo script for The Agent Lab hackathon presentation

set -e

URL=${1:-"https://www.bldr.space"}

echo "═══════════════════════════════════════════════════════════════"
echo "  THE AGENT LAB - LIVE DEMO"
echo "  Marketing Content Pipeline Agent"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Target Business: $URL"
echo "Model: $(grep OPENROUTER_MODEL .env 2>/dev/null | cut -d= -f2 || echo 'Default')"
echo ""
echo "Starting pipeline..."
echo ""

# Run the pipeline
python3 main.py --url "$URL"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  DEMO COMPLETE"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Find latest output directory
LATEST=$(ls -td outputs/*/ 2>/dev/null | head -1)

if [ -n "$LATEST" ]; then
    echo "Output directory: $LATEST"
    echo ""
    echo "📊 Research Summary:"
    python3 -c "import json; d=json.load(open('$LATEST/research.json')); print(f\"  Business: {d['business']['name']}\"); print(f\"  Confidence: {d['confidence_score']:.0%}\"); print(f\"  Personas: {len(d['audience'])}\")" 2>/dev/null || echo "  (Research data available)"
    
    echo ""
    echo "📋 Strategy Overview:"
    python3 -c "import json; d=json.load(open('$LATEST/strategy.json')); print(f\"  Pillars: {len(d['pillars'])}\"); print(f\"  Channels: {len(d['channels'])}\"); print(f\"  Posts: {len(d['calendar'])}\")" 2>/dev/null || echo "  (Strategy data available)"
    
    echo ""
    echo "🔍 Verification Scores:"
    python3 -c "import json; d=json.load(open('$LATEST/verification.json')); print(f\"  Average Score: {d['average_score']:.2f}/1.0\"); print(f\"  Passed: {d['total_passed']}/{d['total_checked']}\"); print(f\"  Modified: {d['total_modified']}\")" 2>/dev/null || echo "  (Verification data available)"
    
    echo ""
    echo "📝 Generated Posts:"
    ls -1 "$LATEST/posts/" 2>/dev/null | head -5 | sed 's/^/  /' || echo "  (No posts generated)"
    
    echo ""
    echo "View full results:"
    echo "  cd $LATEST"
    echo "  cat posts/post_00_linkedin.md"
fi
