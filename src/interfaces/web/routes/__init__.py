"""
Routes Package - Web Interface Blueprints
"""

# Import all blueprints
from .auth import auth_bp
# from .parcels import parcels_bp  # TODO: Implement
# from .manifests import manifests_bp  # TODO: Implement
from .approvals import approvals_bp
# from .chatbot import chatbot_bp  # TODO: Implement
# from .admin import admin_bp  # TODO: Implement
# from .api import api_bp  # TODO: Implement

__all__ = [
    'auth_bp',
    # 'parcels_bp',
    # 'manifests_bp',
    'approvals_bp',
    # 'chatbot_bp',
    # 'admin_bp',
    # 'api_bp',
]
