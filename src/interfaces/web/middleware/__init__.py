"""
Middleware Package
"""
from .auth import (
    login_required,
    role_required,
    admin_required,
    driver_required,
    cs_required,
    depot_manager_required,
)
from .error_handler import register_error_handlers

__all__ = [
    'login_required',
    'role_required',
    'admin_required',
    'driver_required',
    'cs_required',
    'depot_manager_required',
    'register_error_handlers',
]
