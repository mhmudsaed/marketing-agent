"""Launch the web dashboard."""
import uvicorn
from config.settings import settings

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
    uvicorn.run("web.app:app", host="0.0.0.0", port=8000, reload=False)
