"""
Authentication Blueprint - Login, Logout, Demo Routes
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, get_flashed_messages
from functools import wraps
import warnings

from user_manager import UserManager
from parcel_tracking_db import ParcelTrackingDB
from utils.async_helpers import run_async
from src.infrastructure.agents import identity_agent

warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*transport")

auth_bp = Blueprint('auth', __name__)


# Global flag for user initialization
USERS_INITIALIZED = False


async def ensure_users_initialized():
    """Ensure default users exist in database"""
    global USERS_INITIALIZED
    if USERS_INITIALIZED:
        return True
    
    try:
        async with ParcelTrackingDB() as db:
            if not db.database:
                await db.connect()
            
            try:
                await db.database.create_container(
                    id="users",
                    partition_key={"paths": ["/username"], "kind": "Hash"}
                )
            except Exception as e:
                if "already exists" not in str(e).lower():
                    pass  # Container exists
            
            user_mgr = UserManager(db)
            
            default_users = [
                {"username": "admin", "password": "admin123", "role": UserManager.ROLE_ADMIN,
                 "full_name": "System Administrator", "email": "admin@dtlogistics.com.au"},
                {"username": "driver001", "password": "driver123", "role": UserManager.ROLE_DRIVER,
                 "full_name": "John Smith", "email": "john.smith@dtlogistics.com.au", "driver_id": "driver-001"},
                {"username": "driver002", "password": "driver123", "role": UserManager.ROLE_DRIVER,
                 "full_name": "Sarah Jones", "email": "sarah.jones@dtlogistics.com.au", "driver_id": "driver-002"},
                {"username": "driver003", "password": "driver123", "role": UserManager.ROLE_DRIVER,
                 "full_name": "Mike Brown", "email": "mike.brown@dtlogistics.com.au", "driver_id": "driver-003"},
                {"username": "depot_mgr", "password": "depot123", "role": UserManager.ROLE_DEPOT_MANAGER,
                 "full_name": "Lisa Anderson", "email": "lisa.anderson@dtlogistics.com.au"},
                {"username": "support", "password": "support123", "role": UserManager.ROLE_CUSTOMER_SERVICE,
                 "full_name": "Tom Wilson", "email": "support@dtlogistics.com.au"},
            ]
            
            for user_data in default_users:
                try:
                    existing = await user_mgr.get_user_by_username(user_data["username"])
                    if not existing:
                        await user_mgr.create_user(
                            username=user_data["username"],
                            password=user_data["password"],
                            role=user_data["role"],
                            full_name=user_data["full_name"],
                            email=user_data.get("email"),
                            driver_id=user_data.get("driver_id"),
                        )
                except Exception:
                    pass
            
            USERS_INITIALIZED = True
            return True
    except Exception:
        return False


@auth_bp.route("/")
def index():
    """Welcome page"""
    return render_template("demo_welcome.html")


@auth_bp.route("/demo")
def demo_welcome():
    """Alternative route to demo welcome page"""
    return render_template("demo_welcome.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login page with role-based authentication and AI Identity Agent verification"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        async def auth_user():
            await ensure_users_initialized()
            
            async with ParcelTrackingDB() as db:
                if not db.database:
                    await db.connect()
                
                user_mgr = UserManager(db)
                user = await user_mgr.authenticate(username, password)
                
                # If driver, verify with Azure AI Identity Agent
                if user and user.get("role") == UserManager.ROLE_DRIVER:
                    verification_request = {
                        "courier_id": user.get("username"),
                        "name": user.get("full_name"),
                        "role": user.get("role"),
                        "employment_status": "active",
                        "authorized_zone": user.get("store_location", "All"),
                        "verification_method": "credential_login",
                    }
                    
                    try:
                        identity_result = await identity_agent(verification_request)
                        user["ai_verified"] = identity_result.get("success", False)
                    except Exception:
                        user["ai_verified"] = False
                
                return user
        
        try:
            user = run_async(auth_user())
            
            if user:
                session.clear()
                get_flashed_messages()  # Clear old messages
                
                session["user"] = user
                session["logged_in"] = True
                session["username"] = user["username"]
                session.modified = True
                
                if user.get("ai_verified"):
                    flash(f"Welcome back, {user['full_name']}! [AI Verified]", "success")
                else:
                    flash(f"Welcome back, {user['full_name']}!", "success")
                
                next_page = request.args.get("next")
                if next_page:
                    return redirect(next_page)
                
                if user["role"] == UserManager.ROLE_DRIVER:
                    return redirect(url_for("manifests.driver_manifest"))
                else:
                    return redirect(url_for("admin.ai_insights"))
            else:
                flash("Invalid credentials", "danger")
        except Exception as e:
            flash(f"Login error: {str(e)}", "danger")
    
    return render_template("login.html")


@auth_bp.route("/demo-login/<username>")
def demo_login(username):
    """Auto-login for demo users"""
    demo_users = {
        "admin": {"password": "admin123", "role": UserManager.ROLE_ADMIN,
                  "full_name": "System Administrator", "email": "admin@dtlogistics.com.au"},
        "support": {"password": "support123", "role": UserManager.ROLE_CUSTOMER_SERVICE,
                    "full_name": "Support Agent", "email": "support@dtlogistics.com.au"},
        "depot_mgr": {"password": "depot123", "role": UserManager.ROLE_DEPOT_MANAGER,
                      "full_name": "Depot Manager", "email": "lisa.anderson@dtlogistics.com.au"},
        "driver001": {"password": "driver123", "role": UserManager.ROLE_DRIVER,
                      "full_name": "John Smith", "email": "john.smith@dtlogistics.com.au", "driver_id": "driver-001"},
        "driver002": {"password": "driver123", "role": UserManager.ROLE_DRIVER,
                      "full_name": "Sarah Jones", "email": "sarah.jones@dtlogistics.com.au", "driver_id": "driver-002"},
        "driver003": {"password": "driver123", "role": UserManager.ROLE_DRIVER,
                      "full_name": "Mike Brown", "email": "mike.brown@dtlogistics.com.au", "driver_id": "driver-003"},
    }
    
    if username not in demo_users:
        flash("Invalid demo user", "danger")
        return redirect(url_for("auth.index"))
    
    demo_info = demo_users[username]
    
    async def auth_demo_user():
        await ensure_users_initialized()
        
        async with ParcelTrackingDB() as db:
            if not db.database:
                await db.connect()
            
            user_mgr = UserManager(db)
            user = await user_mgr.authenticate(username, demo_info["password"])
            
            if not user:
                try:
                    existing = await user_mgr.get_user_by_username(username)
                    if not existing:
                        await user_mgr.create_user(
                            username=username,
                            password=demo_info["password"],
                            role=demo_info["role"],
                            full_name=demo_info["full_name"],
                            email=demo_info.get("email"),
                            driver_id=demo_info.get("driver_id"),
                        )
                        return await user_mgr.authenticate(username, demo_info["password"])
                except Exception:
                    pass
            
            return user
    
    try:
        user = run_async(auth_demo_user())
        if user:
            session.clear()
            get_flashed_messages()
            
            session["user"] = user
            session["logged_in"] = True
            session["username"] = user["username"]
            session.modified = True
            
            flash(f"Logged in as {user['full_name']} ({username})", "success")
            
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            
            if user["role"] == UserManager.ROLE_DRIVER:
                return redirect(url_for("manifests.driver_manifest"))
            else:
                return redirect(url_for("admin.ai_insights"))
        else:
            flash("Demo login failed", "danger")
    except Exception as e:
        flash(f"Demo login error: {str(e)}", "danger")
    
    return redirect(url_for("auth.index"))


@auth_bp.route("/logout")
def logout():
    """Logout"""
    session.clear()
    session.modified = True
    flash("Successfully logged out", "info")
    return redirect(url_for("auth.index"))


@auth_bp.route("/admin/setup-users-now", methods=["GET"])
def setup_users_now():
    """One-time setup endpoint to create default users"""
    import traceback
    
    try:
        async def do_setup():
            async with ParcelTrackingDB() as db:
                if not db.database:
                    await db.connect()
                
                try:
                    await db.database.create_container(
                        id="users",
                        partition_key={"paths": ["/username"], "kind": "Hash"}
                    )
                    msg = "✅ Users container created<br>"
                except Exception as e:
                    if "already exists" in str(e).lower():
                        msg = "✅ Users container already exists<br>"
                    else:
                        msg = f"Container error: {e}<br>"
                
                user_mgr = UserManager(db)
                
                default_users = [
                    {"username": "admin", "password": "admin123", "role": UserManager.ROLE_ADMIN,
                     "full_name": "System Administrator", "email": "admin@dtlogistics.com.au"},
                    {"username": "support", "password": "support123", "role": UserManager.ROLE_CUSTOMER_SERVICE,
                     "full_name": "Support Agent", "email": "support@dtlogistics.com.au"},
                    {"username": "depot_mgr", "password": "depot123", "role": UserManager.ROLE_DEPOT_MANAGER,
                     "full_name": "Depot Manager", "email": "lisa.anderson@dtlogistics.com.au"},
                    {"username": "driver001", "password": "driver123", "role": UserManager.ROLE_DRIVER,
                     "full_name": "John Smith", "driver_id": "driver-001", "email": "john.smith@dtlogistics.com.au"},
                    {"username": "driver002", "password": "driver123", "role": UserManager.ROLE_DRIVER,
                     "full_name": "Sarah Jones", "driver_id": "driver-002", "email": "sarah.jones@dtlogistics.com.au"},
                    {"username": "driver003", "password": "driver123", "role": UserManager.ROLE_DRIVER,
                     "full_name": "Mike Brown", "driver_id": "driver-003", "email": "mike.brown@dtlogistics.com.au"},
                ]
                
                created = []
                for user_data in default_users:
                    try:
                        existing = await user_mgr.get_user_by_username(user_data["username"])
                        if not existing:
                            await user_mgr.create_user(
                                username=user_data["username"],
                                password=user_data["password"],
                                role=user_data["role"],
                                full_name=user_data["full_name"],
                                driver_id=user_data.get("driver_id"),
                            )
                            created.append(user_data["username"])
                    except Exception as e:
                        msg += f"Error creating {user_data['username']}: {e}<br>"
                
                return msg, created
        
        msg, created = run_async(do_setup())
        return f"""
            <h1>Setup Complete!</h1>
            <p>{msg}</p>
            <p>Created users: {', '.join(created) if created else 'All users already existed'}</p>
            <p><a href='/login'>Go to Login</a></p>
        """
    
    except Exception as e:
        return f"<h1>Setup Failed</h1><p>Error: {str(e)}</p><pre>{traceback.format_exc()}</pre>", 500
