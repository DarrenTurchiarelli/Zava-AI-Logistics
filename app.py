"""
Zava Logistics Web Application
Entry point for Flask web server

This is a thin wrapper that delegates to the modular application structure.
The actual Flask app factory is in src/interfaces/web/app.py
"""
import os
from src.interfaces.web.app import create_app

# Create Flask application
app = create_app()

if __name__ == "__main__":
    # Configuration from environment variables
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV", "production") == "development"
    
    print(f">> Starting Zava Logistics on {host}:{port}")
    print(f"   Debug mode: {debug}")
    print(f"   Environment: {os.getenv('FLASK_ENV', 'production')}")
    
    app.run(
        host=host,
        port=port,
        debug=debug
    )
