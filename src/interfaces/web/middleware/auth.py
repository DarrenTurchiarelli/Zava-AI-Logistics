"""
Authentication Middleware - Login decorators and access control
"""
from functools import wraps
from flask import session, flash, redirect, url_for, request

from user_manager import (
    UserManager,
    has_role,
    is_admin,
    is_driver,
    can_approve_requests,
    can_create_manifest,
    can_view_all_manifests,
)


def login_required(f):
    """Require user to be logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user"):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """Require user to have one of the specified roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = session.get("user")
            if not user:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("auth.login"))
            
            if user.get("role") not in roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("auth.index"))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Require admin role"""
    return role_required(UserManager.ROLE_ADMIN)(f)


def driver_required(f):
    """Require driver role"""
    return role_required(UserManager.ROLE_DRIVER)(f)


def cs_required(f):
    """Require customer service or admin role"""
    return role_required(UserManager.ROLE_CUSTOMER_SERVICE, UserManager.ROLE_ADMIN)(f)


def depot_manager_required(f):
    """Require depot manager or admin role"""
    return role_required(UserManager.ROLE_DEPOT_MANAGER, UserManager.ROLE_ADMIN)(f)
