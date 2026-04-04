#!/bin/bash

# Startup script for Azure App Service
echo "Starting Zava Web Application..."

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Set PYTHONPATH to include src/ directory for new architecture
export PYTHONPATH="${PYTHONPATH}:/home/site/wwwroot:/home/site/wwwroot/src"

# Start Gunicorn server with application factory
echo "Starting Gunicorn server..."
gunicorn --bind=0.0.0.0 --timeout 600 app:app
