#!/bin/bash

# Startup script for Azure App Service
echo "Starting DT Logistics Web Application..."

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Run database migrations if needed
echo "Checking database connection..."

# Start Gunicorn server
echo "Starting Gunicorn server..."
gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers=4 --threads=2 --worker-class=gthread app:app
