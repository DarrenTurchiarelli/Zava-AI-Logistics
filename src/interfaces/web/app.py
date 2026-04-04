"""
Flask Application Factory
Creates and configures the Flask app with all blueprints and middleware
"""
import os
from flask import Flask, session
from pathlib import Path
import logging

from config.company import get_company_info
from utils.logging_config import setup_logging
from src.shared.warning_suppression import setup_warning_suppression

# Import blueprints
from .routes.auth import auth_bp
from .routes.approvals import approvals_bp
from .routes.parcels import parcels_bp
from .routes.manifests import manifests_bp
from .routes.chatbot import chatbot_bp
from .routes.admin import admin_bp
from .routes.api import api_bp

# Import middleware
from .middleware import register_error_handlers


def create_app(config=None):
    """
    Application factory function
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Configured Flask application
    """
    # Create Flask app
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / 'templates'),
        static_folder=str(Path(__file__).parent.parent.parent.parent / 'static'),
    )
    
    # Load configuration
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "dt-logistics-secret-key-change-in-production")
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload
    
    if config:
        app.config.update(config)
    
    # Setup logging
    logger = setup_logging("zava.app")
    
    # Setup warning suppression
    setup_warning_suppression()
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(approvals_bp)
    app.register_blueprint(parcels_bp)
    app.register_blueprint(manifests_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Make company info available to all templates
    @app.context_processor
    def inject_company_info():
        """Inject company information into all templates"""
        return {"company": get_company_info()}
    
    # Add cache control headers for authenticated pages
    @app.after_request
    def add_header(response):
        """Add headers to prevent caching of authenticated pages"""
        if "user" in session:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "-1"
        return response
    
    logger.info("Flask application created successfully")
    
    return app
