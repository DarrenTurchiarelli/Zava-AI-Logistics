"""
User Repository

Repository for User authentication and authorization.
"""

from typing import Dict, List, Optional
from abc import ABC, abstractmethod
import hashlib
import secrets
from datetime import datetime, timezone

from src.domain.exceptions import EntityNotFoundError, DuplicateEntityError
from .base_repository import IQueryableRepository


class User:
    """User model (lightweight, auth-focused)"""
    
    def __init__(
        self,
        id: str,
        username: str,
        password_hash: str,
        salt: str,
        role: str,
        full_name: str,
        email: Optional[str] = None,
        driver_id: Optional[str] = None,
        active: bool = True,
        created_at: Optional[datetime] = None,
        last_login: Optional[datetime] = None
    ):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.salt = salt
        self.role = role
        self.full_name = full_name
        self.email = email
        self.driver_id = driver_id
        self.active = active
        self.created_at = created_at or datetime.now(timezone.utc)
        self.last_login = last_login
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "username": self.username,
            "password_hash": self.password_hash,
            "salt": self.salt,
            "role": self.role,
            "full_name": self.full_name,
            "email": self.email,
            "driver_id": self.driver_id,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "User":
        """Create User from dictionary"""
        created_at = None
        if data.get("created_at") and isinstance(data["created_at"], str):
            created_at = datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
        
        last_login = None
        if data.get("last_login") and isinstance(data["last_login"], str):
            last_login = datetime.fromisoformat(data["last_login"].replace('Z', '+00:00'))
        
        return cls(
            id=data["id"],
            username=data["username"],
            password_hash=data["password_hash"],
            salt=data["salt"],
            role=data["role"],
            full_name=data["full_name"],
            email=data.get("email"),
            driver_id=data.get("driver_id"),
            active=data.get("active", True),
            created_at=created_at,
            last_login=last_login,
        )


class IUserRepository(IQueryableRepository[User], ABC):
    """User repository interface"""
    
    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        pass
    
    @abstractmethod
    async def find_by_role(self, role: str) -> List[User]:
        """Get all users with specific role"""
        pass
    
    @abstractmethod
    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate user and return user info if valid"""
        pass
    
    @abstractmethod
    async def update_last_login(self, username: str) -> None:
        """Update last login timestamp"""
        pass


class CosmosUserRepository(IUserRepository):
    """Cosmos DB implementation of User repository"""
    
    def __init__(self, database_client):
        self.database = database_client
        self.container_name = "users"
        self._container = None
    
    async def _get_container(self):
        """Get container client (lazy initialization)"""
        if self._container is None:
            self._container = self.database.get_container_client(self.container_name)
        return self._container
    
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
        test_hash, _ = CosmosUserRepository.hash_password(password, salt)
        return test_hash == pwd_hash
    
    async def get_by_id(self, id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            container = await self._get_container()
            # Username is partition key, so extract from ID
            username = id.replace("user_", "")
            item = await container.read_item(item=id, partition_key=username)
            return User.from_dict(item)
        except Exception:
            return None
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        container = await self._get_container()
        query = "SELECT * FROM c WHERE c.username = @username AND c.active = true"
        parameters = [{"name": "@username", "value": username}]
        
        items = []
        async for item in container.query_items(
            query=query,
            parameters=parameters,
            partition_key=username
        ):
            items.append(User.from_dict(item))
        
        return items[0] if items else None
    
    async def get_all(self, limit: Optional[int] = None, skip: int = 0) -> List[User]:
        """Get all active users"""
        container = await self._get_container()
        query = "SELECT * FROM c WHERE c.active = true ORDER BY c.username"
        
        if limit:
            query += f" OFFSET {skip} LIMIT {limit}"
        
        users = []
        async for item in container.query_items(query=query):
            users.append(User.from_dict(item))
        
        return users
    
    async def create(self, user: User) -> User:
        """Create a new user"""
        existing = await self.get_by_username(user.username)
        if existing:
            raise DuplicateEntityError("User", user.username)
        
        container = await self._get_container()
        item = user.to_dict()
        created_item = await container.create_item(body=item)
        return User.from_dict(created_item)
    
    async def update(self, user: User) -> User:
        """Update existing user"""
        existing = await self.get_by_id(user.id)
        if not existing:
            raise EntityNotFoundError("User", user.id)
        
        container = await self._get_container()
        item = user.to_dict()
        updated_item = await container.replace_item(item=user.id, body=item)
        return User.from_dict(updated_item)
    
    async def delete(self, id: str) -> bool:
        """Delete (deactivate) user"""
        user = await self.get_by_id(id)
        if not user:
            return False
        
        user.active = False
        await self.update(user)
        return True
    
    async def exists(self, id: str) -> bool:
        """Check if user exists"""
        return await self.get_by_id(id) is not None
    
    async def find_by_criteria(self, criteria: Dict) -> List[User]:
        """Find users matching criteria"""
        container = await self._get_container()
        
        conditions = []
        parameters = []
        
        for i, (key, value) in enumerate(criteria.items()):
            param_name = f"@param{i}"
            conditions.append(f"c.{key} = {param_name}")
            parameters.append({"name": param_name, "value": value})
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM c WHERE {where_clause}"
        
        users = []
        async for item in container.query_items(query=query, parameters=parameters):
            users.append(User.from_dict(item))
        
        return users
    
    async def count(self, criteria: Optional[Dict] = None) -> int:
        """Count users"""
        container = await self._get_container()
        
        if criteria:
            conditions = []
            parameters = []
            
            for i, (key, value) in enumerate(criteria.items()):
                param_name = f"@param{i}"
                conditions.append(f"c.{key} = {param_name}")
                parameters.append({"name": param_name, "value": value})
            
            where_clause = " AND ".join(conditions)
            query = f"SELECT VALUE COUNT(1) FROM c WHERE {where_clause}"
        else:
            query = "SELECT VALUE COUNT(1) FROM c"
            parameters = []
        
        item_list = [item async for item in container.query_items(query=query, parameters=parameters)]
        return item_list[0] if item_list else 0
    
    async def find_by_role(self, role: str) -> List[User]:
        """Get all users with specific role"""
        return await self.find_by_criteria({"role": role, "active": True})
    
    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate user and return user info if valid"""
        user = await self.get_by_username(username)
        if not user:
            return None
        
        if self.verify_password(password, user.password_hash, user.salt):
            # Update last login
            await self.update_last_login(username)
            return user
        
        return None
    
    async def update_last_login(self, username: str) -> None:
        """Update last login timestamp"""
        user = await self.get_by_username(username)
        if user:
            user.last_login = datetime.now(timezone.utc)
            try:
                await self.update(user)
            except Exception as e:
                print(f"[WARN] Could not update last_login for {username}: {e}")
