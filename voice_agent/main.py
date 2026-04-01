"""
Voice Agent - Entry Point
AI-powered voice agent for inbound and outbound calls with Nigerian English voice
"""

import logging
import os
import sys
import asyncio
from pathlib import Path

# Add parent directory to path to allow imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Try relative imports first (for package usage), fall back to absolute
try:
    from .app import create_voice_app
    from .config import VoiceConfig
except ImportError:
    # If relative imports fail, use absolute imports
    from voice_agent.app import create_voice_app
    from voice_agent.config import VoiceConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for voice agent"""
    config = VoiceConfig()
    
    # Create FastAPI app
    app = create_voice_app(config)
    
    # Run the application
    import uvicorn
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()
