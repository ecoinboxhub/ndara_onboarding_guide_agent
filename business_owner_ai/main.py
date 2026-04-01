"""
ndara.ai Business Owner AI - Main Entry Point
Business intelligence and analytics inference server
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for Business Owner AI inference server"""
    try:
        # Import inference API
        from src.api.inference_api import BusinessOwnerInferenceAPI
        
        # Get configuration from environment
        host = os.getenv('API_HOST', '0.0.0.0')
        port = int(os.getenv('API_PORT', 8001))
        
        logger.info("="*60)
        logger.info("ndara.ai Business Owner AI - Inference Server")
        logger.info("="*60)
        logger.info(f"Starting server on {host}:{port}")
        logger.info("API Documentation: http://localhost:8001/docs")
        logger.info("="*60)
        
        # Create and run API
        api = BusinessOwnerInferenceAPI()
        api.run(host=host, port=port)
        
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise


if __name__ == "__main__":
    main()

