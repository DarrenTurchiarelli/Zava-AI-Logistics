"""
Cosmos DB Client

Refactored Azure Cosmos DB connection management with managed identity support.
This module provides the core database client used by all repositories.
"""

import asyncio
import os
from typing import Optional

from azure.cosmos import PartitionKey
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import AzureCliCredential, DefaultAzureCredential, ManagedIdentityCredential
from dotenv import load_dotenv

load_dotenv()

# Global credential cache to avoid re-authentication
_cached_credential = None


def get_cached_credential():
    """Get or create a cached Azure credential to avoid timeout in threads"""
    global _cached_credential
    if _cached_credential is None:
        # Use Managed Identity when explicitly enabled (Azure deployment)
        if os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true":
            _cached_credential = ManagedIdentityCredential()
        else:
            # Running locally - use AzureCliCredential with longer timeout
            _cached_credential = AzureCliCredential(process_timeout=60)
    return _cached_credential


class CosmosDBClient:
    """
    Cosmos DB Client for Zava Logistics
    
    Manages connection to Azure Cosmos DB with support for both key-based
    and managed identity authentication.
    
    Authentication Methods:
    1. Key-based (Local Development):
       - Set COSMOS_CONNECTION_STRING or COSMOS_DB_ENDPOINT + COSMOS_DB_KEY
    
    2. Managed Identity (Azure Production):
       - Set USE_MANAGED_IDENTITY=true
       - Set COSMOS_DB_ENDPOINT and COSMOS_DB_DATABASE_NAME
       - Required RBAC: Cosmos DB Built-in Data Contributor
    """
    
    def __init__(self):
        # Try to get connection details
        self.endpoint = os.getenv("COSMOS_DB_ENDPOINT")
        self.key = os.getenv("COSMOS_DB_KEY")
        
        # If not available, parse from connection string
        if not self.endpoint or not self.key:
            connection_string = os.getenv("COSMOS_CONNECTION_STRING")
            if connection_string:
                parts = dict(part.split("=", 1) for part in connection_string.split(";") if "=" in part)
                self.endpoint = parts.get("AccountEndpoint", "").rstrip("/")
                self.key = parts.get("AccountKey", "")
        
        self.database_name = os.getenv("COSMOS_DB_DATABASE_NAME", "agent_workflow_db")
        
        # Connection objects
        self.client: Optional[CosmosClient] = None
        self.database = None
        self.credential = None
        self.using_azure_ad = False
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def connect(self) -> None:
        """
        Initialize connection to Cosmos DB
        
        Tries key-based authentication first, falls back to managed identity.
        """
        try:
            if not self.endpoint:
                raise ValueError("COSMOS_DB_ENDPOINT or COSMOS_CONNECTION_STRING environment variable is required")
            
            # Try key-based authentication first
            if self.key:
                # Check if forcing key auth
                force_key_auth = os.getenv("FORCE_KEY_AUTH", "false").lower() == "true"
                
                try:
                    self.client = CosmosClient(self.endpoint, self.key)
                    self.database = await self.client.create_database_if_not_exists(
                        id=self.database_name, offer_throughput=400
                    )
                    if os.getenv("DEBUG_MODE") == "true":
                        print(f"✓ Connected to Cosmos DB using account key")
                
                except Exception as key_error:
                    # If forcing key auth, don't fall back
                    if force_key_auth:
                        print(f"[ERROR] Key-based authentication failed (FORCE_KEY_AUTH=true)")
                        raise key_error
                    
                    # Fall back to Azure AD if local auth disabled
                    if "Local Authorization is disabled" in str(key_error):
                        if os.getenv("DEBUG_MODE") == "true":
                            print(f"[WARN] Key-based auth disabled, trying Azure AD...")
                        
                        self.credential = get_cached_credential()
                        self.client = CosmosClient(self.endpoint, self.credential)
                        self.using_azure_ad = True
                        self.database = self.client.get_database_client(self.database_name)
                        
                        if os.getenv("DEBUG_MODE") == "true":
                            print(f"✓ Connected to Cosmos DB using Azure AD")
                    else:
                        raise key_error
            else:
                # No key - use Azure AD
                if os.getenv("DEBUG_MODE") == "true":
                    print(f"[WARN] No account key found, using Azure AD authentication...")
                
                self.credential = get_cached_credential()
                self.client = CosmosClient(self.endpoint, self.credential)
                self.using_azure_ad = True
                self.database = self.client.get_database_client(self.database_name)
                
                if os.getenv("DEBUG_MODE") == "true":
                    print(f"✓ Connected to Cosmos DB using Azure AD")
            
            # Create containers if not using Azure AD (which may lack permissions)
            if not self.using_azure_ad:
                await self._create_containers()
        
        except Exception as e:
            print(f"[ERROR] Failed to connect to Cosmos DB: {e}")
            raise
    
    async def _create_containers(self) -> None:
        """Create all required containers with appropriate partition keys"""
        containers = [
            {"id": "parcels", "partition_key": PartitionKey(path="/store_location")},
            {"id": "tracking_events", "partition_key": PartitionKey(path="/barcode")},
            {"id": "delivery_attempts", "partition_key": PartitionKey(path="/barcode")},
            {"id": "feedback", "partition_key": PartitionKey(path="/tracking_number")},
            {"id": "company_info", "partition_key": PartitionKey(path="/info_type")},
            {"id": "suspicious_messages", "partition_key": PartitionKey(path="/report_date")},
            {"id": "address_history", "partition_key": PartitionKey(path="/address_normalized")},
            {"id": "users", "partition_key": PartitionKey(path="/username")},
            {"id": "Manifests", "partition_key": PartitionKey(path="/manifest_id")},
            {"id": "address_notes", "partition_key": PartitionKey(path="/address_normalized")},
        ]
        
        for container_spec in containers:
            try:
                await self.database.create_container_if_not_exists(
                    id=container_spec["id"],
                    partition_key=container_spec["partition_key"],
                )
                if os.getenv("DEBUG_MODE") == "true":
                    print(f"✓ Container ready: {container_spec['id']}")
            except Exception as e:
                # Log but don't fail - containers might exist
                if os.getenv("DEBUG_MODE") == "true":
                    print(f"⚠️  Container {container_spec['id']}: {str(e)[:100]}")
    
    async def close(self) -> None:
        """Close database connections and cleanup resources"""
        try:
            if self.client:
                # Properly close the aiohttp client session
                if hasattr(self.client, "_client_connection"):
                    try:
                        connection = self.client._client_connection
                        if connection and not connection.closed:
                            await connection.close()
                    except Exception:
                        pass
                
                # Close the Cosmos client
                if hasattr(self.client, "close"):
                    try:
                        result = self.client.close()
                        if hasattr(result, "__await__"):
                            await result
                    except Exception:
                        pass
                self.client = None
            
            if self.credential:
                if hasattr(self.credential, "close") and callable(getattr(self.credential, "close")):
                    try:
                        if asyncio.iscoroutinefunction(self.credential.close):
                            await self.credential.close()
                        else:
                            self.credential.close()
                    except Exception:
                        pass
                self.credential = None
        except Exception:
            # Silently ignore close errors
            pass
    
    def get_container_client(self, container_name: str):
        """Get a container client for repository use"""
        if not self.database:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.database.get_container_client(container_name)


# Singleton instance for convenience
_cosmos_client_instance: Optional[CosmosDBClient] = None


async def get_cosmos_client() -> CosmosDBClient:
    """
    Get or create the global Cosmos DB client instance
    
    Returns:
        Connected CosmosDBClient instance
    """
    global _cosmos_client_instance
    
    if _cosmos_client_instance is None:
        _cosmos_client_instance = CosmosDBClient()
        await _cosmos_client_instance.connect()
    
    return _cosmos_client_instance


async def close_cosmos_client() -> None:
    """Close the global Cosmos DB client"""
    global _cosmos_client_instance
    
    if _cosmos_client_instance:
        await _cosmos_client_instance.close()
        _cosmos_client_instance = None
