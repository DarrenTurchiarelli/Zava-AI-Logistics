"""
Microsoft Agent Framework v1.0 integration layer for Zava.

This package wraps all MAF primitives:
  - AzureAIClient-based agent callers  (maf/client.py)
  - @tool-decorated Cosmos DB tools    (maf/tools.py)
  - Logging middleware                  (maf/middleware.py)
  - SequentialBuilder / HandoffBuilder workflows (maf/workflows.py)
"""

from .client import call_maf_agent, make_chat_client
from .middleware import LoggingMiddleware
from .tools import (
    track_parcel,
    search_parcels_by_recipient,
    search_parcels_by_driver,
    get_delivery_statistics,
    get_pending_parcels_for_dispatch,
    get_available_drivers,
    get_performance_metrics,
    update_delivery_status,
)
from .workflows import run_fraud_workflow

__all__ = [
    "call_maf_agent",
    "make_chat_client",
    "LoggingMiddleware",
    "track_parcel",
    "search_parcels_by_recipient",
    "search_parcels_by_driver",
    "get_delivery_statistics",
    "get_pending_parcels_for_dispatch",
    "get_available_drivers",
    "get_performance_metrics",
    "update_delivery_status",
    "run_fraud_workflow",
]
