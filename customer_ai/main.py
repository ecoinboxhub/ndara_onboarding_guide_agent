"""
ndara.ai Customer AI - Main Entry Point
Minimal inference API server
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Import FastAPI app for gunicorn
from src.api.inference_api import create_app
app = create_app()


def main():
    """Main entry point for Customer AI inference server"""
    import uvicorn

    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', 8000))

    logger.info("=" * 60)
    logger.info("ndara.ai Customer AI - Inference Server")
    logger.info("=" * 60)
    logger.info(f"Starting server on {host}:{port}")
    logger.info(f"Log level: {log_level}")
    logger.info("API Documentation: http://{}:{}/docs".format(host, port))
    logger.info("=" * 60)

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
