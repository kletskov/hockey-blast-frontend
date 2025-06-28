import os

# Get port from environment variable (Render sets this)
port = int(os.environ.get('PORT', 8000))

# Bind to the correct port on all interfaces
bind = f"0.0.0.0:{port}"
workers = 4
threads = 2
timeout = 120

# Logging
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stderr
loglevel = 'info'

# Enable debug logging if DEBUG_MODE is set
if os.environ.get('DEBUG_MODE', '').lower() in ('true', '1', 'yes', 'on'):
    loglevel = 'debug'
