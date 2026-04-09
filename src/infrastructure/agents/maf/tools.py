"""
MAF @tool-decorated wrappers around the existing Cosmos DB tool functions.

The existing implementations in cosmos_tools.py are intentionally synchronous
(they run inside a ThreadPoolExecutor in the legacy polling loop).  Here we
thin-wrap them with the @tool decorator so MAF's function-calling layer can
discover, describe, and invoke them automatically.

All tool functions remain synchronous — MAF calls them in a thread pool.
"""

from agent_framework import tool

# ---------------------------------------------------------------------------
# Import underlying implementations (sync, Cosmos DB backed)
# ---------------------------------------------------------------------------
from src.infrastructure.agents.tools.cosmos_tools import (
    track_parcel_tool,
    search_parcels_by_recipient_tool,
    search_parcels_by_driver_tool,
    get_delivery_statistics_tool,
    get_pending_parcels_for_dispatch_tool,
    get_available_drivers_tool,
    get_performance_metrics_tool,
    update_delivery_status_tool,
)


# ---------------------------------------------------------------------------
# Customer Service tools
# ---------------------------------------------------------------------------


@tool
def track_parcel(tracking_number: str) -> str:
    """
    Look up a parcel in real time by its tracking number.

    Returns the current status, location, estimated delivery window,
    lodgement photos and delivery photos (if available), and a full
    event history for the parcel.

    Args:
        tracking_number: The parcel tracking number (e.g. LP123456 or DT202512170037).
    """
    return track_parcel_tool(tracking_number)


@tool
def search_parcels_by_recipient(
    name: str = "",
    postcode: str = "",
    address: str = "",
) -> str:
    """
    Search for parcels by recipient details.

    Provide at least one of name, postcode, or address.  Returns a
    list of matching parcels with their current status and tracking numbers.

    Args:
        name: Recipient's full or partial name.
        postcode: Recipient's postcode / ZIP code.
        address: Partial or full delivery address.
    """
    return search_parcels_by_recipient_tool(name=name, postcode=postcode, address=address)


@tool
def search_parcels_by_driver(driver_id: str) -> str:
    """
    Return all parcels currently assigned to a specific driver.

    Args:
        driver_id: The driver's unique identifier.
    """
    return search_parcels_by_driver_tool(driver_id)


# ---------------------------------------------------------------------------
# Operations / Dispatcher tools
# ---------------------------------------------------------------------------


@tool
def get_delivery_statistics(state: str = "", period: str = "today") -> str:
    """
    Retrieve delivery statistics for a state and time period.

    Args:
        state: Australian state code (NSW, VIC, QLD, WA, SA, TAS, ACT, NT).
               Leave empty for nation-wide statistics.
        period: One of 'today', 'week', or 'month'.
    """
    return get_delivery_statistics_tool(state=state, period=period)


@tool
def get_pending_parcels_for_dispatch(state: str = "") -> str:
    """
    List parcels that are at a depot and ready to be assigned to a driver.

    Args:
        state: Filter by state code.  Leave empty for all states.
    """
    return get_pending_parcels_for_dispatch_tool(state=state)


@tool
def get_available_drivers(state: str = "") -> str:
    """
    List drivers who are currently available to take deliveries.

    Args:
        state: Filter by state code.  Leave empty for all states.
    """
    return get_available_drivers_tool(state=state)


@tool
def get_performance_metrics(period: str = "week") -> str:
    """
    Return KPIs such as on-time delivery rate, average delivery time,
    and customer satisfaction scores.

    Args:
        period: One of 'today', 'week', or 'month'.
    """
    return get_performance_metrics_tool(period=period)


@tool
def update_delivery_status(
    tracking_number: str,
    new_status: str,
    notes: str = "",
) -> str:
    """
    Update the delivery status of a parcel.

    Args:
        tracking_number: The parcel's tracking number.
        new_status: Target status (e.g. 'delivered', 'failed_delivery', 'returned').
        notes: Optional driver or operator notes to attach.
    """
    return update_delivery_status_tool(
        tracking_number=tracking_number,
        new_status=new_status,
        notes=notes,
    )
