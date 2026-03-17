"""
User Management System for Zava
Handles authentication, authorization, and user roles
"""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class UserManager:
    """Manage users with role-based access control"""

    # User roles
    ROLE_ADMIN = "admin"
    ROLE_DRIVER = "driver"
    ROLE_DEPOT_MANAGER = "depot_manager"
    ROLE_CUSTOMER_SERVICE = "customer_service"

    def __init__(self, db):
        """Initialize with database connection"""
        self.db = db

    @staticmethod
    def hash_password(password: str, salt: str = None) -> tuple:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_hex(16)

        pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return pwd_hash.hex(), salt

    @staticmethod
    def verify_password(password: str, pwd_hash: str, salt: str) -> bool:
        """Verify password against hash"""
        test_hash, _ = UserManager.hash_password(password, salt)
        return test_hash == pwd_hash

    async def create_user(
        self, username: str, password: str, role: str, full_name: str, email: str = None, driver_id: str = None
    ) -> Dict[str, Any]:
        """Create new user account"""
        # Hash password
        pwd_hash, salt = self.hash_password(password)

        # Create user document
        user = {
            "id": f"user_{username}",
            "username": username,
            "password_hash": pwd_hash,
            "salt": salt,
            "role": role,
            "full_name": full_name,
            "email": email,
            "driver_id": driver_id,  # For driver accounts
            "active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": None,
        }

        # Store in database
        container = self.db.database.get_container_client("users")
        await container.create_item(body=user)

        return user

    async def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user and return user info if valid"""
        try:
            container = self.db.database.get_container_client("users")

            # Find user — supply partition_key so this is a single-partition read
            query = "SELECT * FROM c WHERE c.username = @username AND c.active = true"
            parameters = [{"name": "@username", "value": username}]

            async for user in container.query_items(
                query=query,
                parameters=parameters,
                partition_key=username,
            ):
                # Verify password
                if self.verify_password(password, user["password_hash"], user["salt"]):
                    # Update last login (non-fatal — don't block login on this)
                    try:
                        user["last_login"] = datetime.now(timezone.utc).isoformat()
                        await container.replace_item(item=user["id"], body=user)
                    except Exception as update_err:
                        print(f"[WARN] Could not update last_login for {username}: {update_err}")

                    # Return user info (without sensitive data)
                    return {
                        "id": user["id"],
                        "username": user["username"],
                        "role": user["role"],
                        "full_name": user["full_name"],
                        "email": user.get("email"),
                        "driver_id": user.get("driver_id"),
                    }

            return None

        except Exception as e:
            print(f"[ERROR] Authentication error: {e}")
            return None

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        try:
            container = self.db.database.get_container_client("users")

            query = "SELECT * FROM c WHERE c.username = @username"
            parameters = [{"name": "@username", "value": username}]

            async for user in container.query_items(
                query=query,
                parameters=parameters,
                partition_key=username,
            ):
                return user

            return None

        except Exception as e:
            print(f"[ERROR] Error fetching user: {e}")
            return None

    async def update_password(self, username: str, new_password: str) -> bool:
        """Update user password"""
        try:
            user = await self.get_user_by_username(username)
            if not user:
                return False

            # Hash new password
            pwd_hash, salt = self.hash_password(new_password)
            user["password_hash"] = pwd_hash
            user["salt"] = salt

            # Update in database
            container = self.db.database.get_container_client("users")
            await container.replace_item(item=user["id"], body=user)

            return True

        except Exception as e:
            print(f"[ERROR] Error updating password: {e}")
            return False

    async def deactivate_user(self, username: str) -> bool:
        """Deactivate user account"""
        try:
            user = await self.get_user_by_username(username)
            if not user:
                return False

            user["active"] = False

            container = self.db.database.get_container_client("users")
            await container.replace_item(item=user["id"], body=user)

            return True

        except Exception as e:
            print(f"[ERROR] Error deactivating user: {e}")
            return False

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users (admin only)"""
        try:
            container = self.db.database.get_container_client("users")
            query = "SELECT * FROM c ORDER BY c.created_at DESC"

            users = []
            async for user in container.query_items(query=query):
                # Remove sensitive data
                safe_user = {
                    "id": user["id"],
                    "username": user["username"],
                    "role": user["role"],
                    "full_name": user["full_name"],
                    "email": user.get("email"),
                    "active": user["active"],
                    "created_at": user["created_at"],
                    "last_login": user.get("last_login"),
                }
                users.append(safe_user)

            return users

        except Exception as e:
            print(f"[ERROR] Error fetching users: {e}")
            return []


# Role-based access control utilities


def has_role(user: Dict[str, Any], *roles: str) -> bool:
    """Check if user has any of the specified roles"""
    return user.get("role") in roles


def is_admin(user: Dict[str, Any]) -> bool:
    """Check if user is admin"""
    return user.get("role") == UserManager.ROLE_ADMIN


def is_driver(user: Dict[str, Any]) -> bool:
    """Check if user is driver"""
    return user.get("role") == UserManager.ROLE_DRIVER


def can_view_all_manifests(user: Dict[str, Any]) -> bool:
    """Check if user can view all manifests"""
    return has_role(user, UserManager.ROLE_ADMIN, UserManager.ROLE_DEPOT_MANAGER)


def can_create_manifest(user: Dict[str, Any]) -> bool:
    """Check if user can create manifests"""
    return has_role(user, UserManager.ROLE_ADMIN, UserManager.ROLE_DEPOT_MANAGER)


def can_approve_requests(user: Dict[str, Any]) -> bool:
    """Check if user can approve requests"""
    return has_role(user, UserManager.ROLE_ADMIN, UserManager.ROLE_DEPOT_MANAGER)
