"""
Async Utilities for Flask Integration

Centralized async/await helpers for running async functions in synchronous Flask contexts.
Optimized for performance and proper resource cleanup.
"""

import asyncio
from typing import Any, Coroutine


def run_async(coro: Coroutine) -> Any:
    """
    Optimized async runner for Flask routes
    
    Uses asyncio.run() which is more efficient than creating/destroying loops.
    Note: asyncio.run() automatically handles cleanup and is the recommended approach
    for running async code from synchronous contexts in Python 3.7+.
    
    Args:
        coro: Coroutine to execute
        
    Returns:
        Result of coroutine execution
        
    Example:
        result = run_async(database_query())
    """
    try:
        return asyncio.run(coro)
    except RuntimeError as e:
        if "cannot schedule new futures after shutdown" in str(e) or "no running event loop" in str(e):
            # Fallback: create new loop only if absolutely necessary
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        raise
