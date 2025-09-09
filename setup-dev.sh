#!/bin/bash

# Development setup script for hockey-blast-frontend
# This installs the editable version of hockey-blast-common-lib for development

echo "Setting up development environment..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
fi

# Install development requirements
echo "Installing development requirements..."
pip install -r requirements-dev.txt

echo "Development setup complete!"
echo "The hockey-blast-common-lib is now installed in editable mode."
echo "Any changes to the common lib will be immediately available."