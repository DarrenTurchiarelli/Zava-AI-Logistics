"""
Base Repository Interface

Abstract base class for all repositories following the repository pattern.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar

T = TypeVar('T')


class IRepository(ABC, Generic[T]):
    """
    Abstract repository interface
    
    Defines standard CRUD operations for domain entities.
    Concrete implementations handle persistence details (Cosmos DB, etc.)
    """
    
    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        """
        Retrieve entity by ID
        
        Args:
            id: Unique identifier
            
        Returns:
            Entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_all(self, limit: Optional[int] = None, skip: int = 0) -> List[T]:
        """
        Retrieve all entities (with optional pagination)
        
        Args:
            limit: Maximum number of results
            skip: Number of results to skip
            
        Returns:
            List of entities
        """
        pass
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """
        Create a new entity
        
        Args:
            entity: Entity to create
            
        Returns:
            Created entity (may include generated fields)
            
        Raises:
            DuplicateEntityError: If entity already exists
        """
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        """
        Update an existing entity
        
        Args:
            entity: Entity with updated data
            
        Returns:
            Updated entity
            
        Raises:
            EntityNotFoundError: If entity doesn't exist
        """
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """
        Delete an entity by ID
        
        Args:
            id: Entity identifier
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def exists(self, id: str) -> bool:
        """
        Check if entity exists
        
        Args:
            id: Entity identifier
            
        Returns:
            True if entity exists
        """
        pass


class IQueryableRepository(IRepository[T], ABC):
    """
    Extended repository interface with query capabilities
    """
    
    @abstractmethod
    async def find_by_criteria(self, criteria: Dict[str, Any]) -> List[T]:
        """
        Find entities matching criteria
        
        Args:
            criteria: Dictionary of field-value pairs to match
            
        Returns:
            List of matching entities
        """
        pass
    
    @abstractmethod
    async def count(self, criteria: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities matching optional criteria
        
        Args:
            criteria: Optional filter criteria
            
        Returns:
            Count of matching entities
        """
        pass
