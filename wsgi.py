"""
WSGI entry point for the Hockey Blast application.
This file instantiates the application once and exposes it for Gunicorn to use.
"""
import os
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Initializing WSGI application")

# Import the application factory
from app import create_prod_app

# Create the application once at import time
logger.info("Creating application instance")
application = create_prod_app()

# This is the object that Gunicorn will use
app = application

if __name__ == "__main__":
    # For local development only
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting development server on port {port}")
    app.run(host="0.0.0.0", port=port)
