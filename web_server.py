"""Launch the web dashboard."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import uvicorn

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║    🚀 MARKETING CONTENT PIPELINE - WEB DASHBOARD             ║
║                                                              ║
║    Open http://localhost:8000 in your browser                ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    uvicorn.run("web.app:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
