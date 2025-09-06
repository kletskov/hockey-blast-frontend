"""
WSGI entry point for the Hockey Blast application.
This file instantiates the application once and exposes it for Gunicorn to use.
"""
import os
import logging
from dotenv import load_dotenv

# Load production environment variables
load_dotenv('.env.production')
print("Loading environment variables from .env.production")

# Set up basic logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.info("Initializing WSGI application for PRODUCTION")

# Import the application factory
from app import create_prod_app

# Create the application once at import time
logger.info("Creating production application instance")
application = create_prod_app()

# This is the object that Gunicorn will use
app = application
