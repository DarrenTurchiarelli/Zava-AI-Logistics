"""
Customer Service AI Chatbot
Provides AI-powered assistance for customer service representatives
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import config.company as config
from agents.base import customer_service_agent


class CustomerServiceChatbot:
    """AI Chatbot for customer service operations"""

    def __init__(self, db):
        """Initialize chatbot with database connection"""
        self.db = db
        self.conversation_history = []

    async def process_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process customer service query using AI agent

        Args:
            query: The customer service representative's question or request
            context: Additional context like tracking numbers, customer info, etc.

        Returns:
            AI response with relevant information and actions
        """
        # Check if this is public mode (regular user, not customer service)
        is_public = context.get("public_mode", False) if context else False

        # Retrieve relevant parcel data if tracking number mentioned or for context
        parcel_data = None
        if context and context.get("tracking_number"):
            parcel_data = await self._get_parcel_data(context.get("tracking_number"))
        else:
            # Try to extract tracking number from query
            import re

            tracking_pattern = r"\b(DTVIC\d+|DT\d+)\b"
            matches = re.findall(tracking_pattern, query, re.IGNORECASE)
            if matches:
                print(f"📦 Extracted tracking number from query: {matches[0]}")
                parcel_data = await self._get_parcel_data(matches[0].upper())
            else:
                print(f"🔍 No tracking number found in query: {query}")

        # Build enhanced query with context and parcel data
        enhanced_query = self._build_enhanced_query(query, context, is_public, parcel_data)

        # Add to conversation history
        self.conversation_history.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "query": query,
                "context": context,
                "parcel_data_included": parcel_data is not None,
            }
        )

        # Prepare agent request
        agent_request = {
            "customer_name": context.get("customer_name", "Customer") if context else "Customer",
            "issue_type": "inquiry",
            "details": enhanced_query,
        }

        # Only include tracking number and internal data for non-public requests
        if not is_public:
            agent_request["tracking_number"] = context.get("tracking_number") if context else None
            agent_request["preferred_resolution"] = context.get("preferred_resolution") if context else None

        # Call AI agent
        response = await customer_service_agent(agent_request)

        # Add response to history
        self.conversation_history.append({"timestamp": datetime.utcnow().isoformat(), "response": response})

        return response

    async def _get_parcel_data(self, tracking_number: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve parcel data from CosmosDB for AI reasoning

        Args:
            tracking_number: The parcel tracking number

        Returns:
            Parcel data with tracking events or None if not found
        """
        print(f"🔎 Looking up parcel data for: {tracking_number}")
        try:
            # Get parcel from database
            parcels_container = self.db.database.get_container_client("parcels")

            query = "SELECT * FROM c WHERE c.tracking_number = @tracking_number"
            parameters = [{"name": "@tracking_number", "value": tracking_number}]

            items = []
            async for item in parcels_container.query_items(query=query, parameters=parameters):
                items.append(item)

            if not items:
                print(f"❌ No parcel found for tracking number: {tracking_number}")
                return None

            print(f"✅ Found parcel: {tracking_number}")
            parcel = items[0]

            # Get tracking events
            events_container = self.db.database.get_container_client("tracking_events")

            events_query = "SELECT * FROM c WHERE c.tracking_number = @tracking_number ORDER BY c.timestamp DESC"
            events = []
            async for event in events_container.query_items(query=events_query, parameters=parameters):
                events.append(event)

            # Build comprehensive parcel data for AI
            parcel_data = {
                "tracking_number": parcel.get("tracking_number"),
                "status": parcel.get("status"),
                "sender": parcel.get("sender", {}),
                "recipient": parcel.get("recipient", {}),
                "current_location": parcel.get("current_location"),
                "destination": parcel.get("destination"),
                "estimated_delivery": parcel.get("estimated_delivery"),
                "created_at": parcel.get("created_at"),
                "weight": parcel.get("weight"),
                "dimensions": parcel.get("dimensions"),
                "service_type": parcel.get("service_type"),
                "recent_events": events[:10] if events else [],  # Last 10 events
                "total_events": len(events),
                "delivery_photos": parcel.get("delivery_photos", []),  # Include delivery photos
            }

            return parcel_data

        except Exception as e:
            print(f"Error retrieving parcel data: {str(e)}")
            return None

    def _build_enhanced_query(
        self,
        query: str,
        context: Dict[str, Any] = None,
        is_public: bool = False,
        parcel_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build enhanced query with context and parcel data"""
        parts = []

        # Add company information context for AI
        parts.append(f"=== {config.COMPANY_NAME} COMPANY INFORMATION ===")
        parts.append(f"Company: {config.COMPANY_NAME} - {config.COMPANY_TAGLINE}")
        parts.append(f"ABN: {config.COMPANY_ABN}")
        parts.append(f"Phone: {config.COMPANY_PHONE}")
        parts.append(f"Email: {config.COMPANY_EMAIL}")
        parts.append(f"Address: {config.COMPANY_ADDRESS_FULL}")
        parts.append(f"Website: {config.COMPANY_WEBSITE}")
        parts.append(f"Support: {config.SUPPORT_HOURS}")
        parts.append(f"Business Hours: {config.BUSINESS_HOURS}")
        parts.append(f"Weekend Hours: {config.BUSINESS_HOURS_WEEKEND}")
        parts.append("Service Areas: NSW, VIC, QLD, SA, WA, TAS, NT, ACT (All Australian states)")
        parts.append("=== END COMPANY INFO ===\n")

        # Add public mode instruction for AI
        if is_public:
            parts.append(
                "IMPORTANT: This is a public customer inquiry via chat widget. Provide helpful, friendly, conversational responses about Zava services, tracking, delivery times, and general questions. Use the company information above to answer questions. If the customer provides a tracking number or asks to track a parcel, use the parcel data provided below to give them detailed tracking information including current status, location, estimated delivery, and any delivery photos if available. If a customer asks about proof of delivery and photos are available, confirm that delivery photos were captured. Be concise and natural - respond like a helpful customer service agent. Focus on what matters to the customer: where their parcel is, when it will arrive, its current status, and proof of delivery."
            )
            parts.append("")
        else:
            parts.append(
                "IMPORTANT: This is an internal customer service representative inquiry. Provide detailed information including access to parcel tracking data, delivery photos, and internal systems. Be professional and comprehensive. Respond in natural conversational language, not structured formats. If delivery photos are available, inform the agent so they can view them in the interface."
            )
            parts.append("")

        parts.append(f"Customer Question: {query}")

        # Check if query mentions a tracking number that wasn't found in pre-lookup
        if not parcel_data:
            import re

            tracking_pattern = r"\b([A-Z]{2}\d+|[A-Z]+\d+[A-Z]+)\b"
            matches = re.findall(tracking_pattern, query)
            if matches:
                parts.append(f"\n**IMPORTANT**: Customer mentioned tracking number(s): {', '.join(matches)}")
                parts.append(
                    "You MUST use the track_parcel function to look up this parcel information from the database."
                )
                parts.append(
                    "Call track_parcel with the tracking number to get current status, delivery photos, and all parcel details."
                )
                parts.append("")

        # Add parcel data for AI reasoning - INCLUDE FOR PUBLIC USERS when tracking
        if parcel_data:
            parts.append("\n=== PARCEL DATA FROM DATABASE ===")
            parts.append(f"Tracking Number: {parcel_data.get('tracking_number')}")
            parts.append(f"Status: {parcel_data.get('status')}")
            parts.append(f"Current Location: {parcel_data.get('current_location')}")
            parts.append(f"Destination: {parcel_data.get('destination')}")
            parts.append(f"Estimated Delivery: {parcel_data.get('estimated_delivery')}")
            parts.append(f"Service Type: {parcel_data.get('service_type')}")

            # Only include sender/recipient details for internal users
            if not is_public:
                if parcel_data.get("sender"):
                    sender = parcel_data["sender"]
                    if isinstance(sender, dict):
                        parts.append(f"Sender: {sender.get('name', 'N/A')} - {sender.get('address', 'N/A')}")
                    else:
                        parts.append(f"Sender: {sender}")

                if parcel_data.get("recipient"):
                    recipient = parcel_data["recipient"]
                    if isinstance(recipient, dict):
                        parts.append(f"Recipient: {recipient.get('name', 'N/A')} - {recipient.get('address', 'N/A')}")
                    else:
                        parts.append(f"Recipient: {recipient}")

                if parcel_data.get("weight"):
                    parts.append(f"Weight: {parcel_data.get('weight')} kg")

                if parcel_data.get("dimensions"):
                    dims = parcel_data["dimensions"]
                    if isinstance(dims, dict):
                        parts.append(f"Dimensions: {dims.get('length')}x{dims.get('width')}x{dims.get('height')} cm")
                    else:
                        parts.append(f"Dimensions: {dims}")
            else:
                # For public users, include recipient name (but not full address for privacy)
                if parcel_data.get("recipient"):
                    recipient = parcel_data["recipient"]
                    if isinstance(recipient, dict):
                        parts.append(f"Recipient: {recipient.get('name', 'N/A')}")
                    else:
                        parts.append(f"Recipient: {recipient}")

            # Add recent tracking events
            if parcel_data.get("recent_events"):
                parts.append(
                    f"\nRecent Tracking Events (showing {len(parcel_data['recent_events'])} of {parcel_data.get('total_events', 0)}):"
                )
                for idx, event in enumerate(parcel_data["recent_events"][:5], 1):
                    parts.append(
                        f"{idx}. [{event.get('timestamp')}] {event.get('status')} - {event.get('location')} - {event.get('description', 'N/A')}"
                    )

            # Add delivery photo information - AVAILABLE FOR PUBLIC USERS
            if parcel_data.get("delivery_photos"):
                photos = parcel_data["delivery_photos"]
                if is_public:
                    parts.append(f"\nDelivery Photos: {len(photos)} photo(s) ON FILE for this parcel")
                    parts.append(
                        f"NOTE: Photos cannot be displayed in this chat. Tell the customer: 'We have a delivery photo on file. If you'd like a copy, please contact our customer service team at {config.COMPANY_PHONE} or {config.COMPANY_EMAIL}'"
                    )
                else:
                    parts.append(f"\nDelivery Photos: {len(photos)} photo(s) available")
                    for idx, photo in enumerate(photos, 1):
                        parts.append(
                            f"  Photo {idx}: Uploaded by {photo.get('uploaded_by', 'unknown')} at {photo.get('timestamp', 'unknown time')}"
                        )
                    parts.append(
                        "IMPORTANT: Photos will be automatically displayed in the chat below your response. Do NOT tell the user to view them elsewhere - they are already visible in the chat."
                    )

            # Add lodgement photo information
            if parcel_data.get("lodgement_photos"):
                photos = parcel_data["lodgement_photos"]
                if is_public:
                    parts.append(f"\nLodgement Photos: {len(photos)} photo(s) ON FILE for this parcel")
                    parts.append(
                        f"NOTE: Photos cannot be displayed in this chat. Tell the customer: 'We have a lodgement photo on file showing when the parcel was dropped off. If you'd like a copy, please contact our customer service team at {config.COMPANY_PHONE} or {config.COMPANY_EMAIL}'"
                    )
                else:
                    parts.append(f"\nLodgement Photos: {len(photos)} photo(s) available")
                    for idx, photo in enumerate(photos, 1):
                        parts.append(
                            f"  Photo {idx}: Uploaded by {photo.get('uploaded_by', 'unknown')} at {photo.get('timestamp', 'unknown time')}"
                        )
                    parts.append(
                        "IMPORTANT: Lodgement photos will be automatically displayed in the chat below your response."
                    )

            parts.append("=== END PARCEL DATA ===\n")

        if context and not is_public:
            # Only add internal context for customer service users
            if context.get("tracking_number") and not parcel_data:
                parts.append(f"\nTracking Number: {context['tracking_number']}")
            if context.get("customer_name"):
                parts.append(f"Customer: {context['customer_name']}")
            if context.get("additional_info"):
                parts.append(f"Additional Context: {context['additional_info']}")

        return "\n".join(parts)

    async def track_parcel(self, tracking_number: str) -> Dict[str, Any]:
        """
        Track a parcel and get its current status

        Args:
            tracking_number: The parcel tracking number

        Returns:
            Parcel information including status, location, and history
        """
        try:
            # Get parcel from database
            parcels_container = self.db.database.get_container_client("parcels")

            query = f"SELECT * FROM c WHERE c.tracking_number = @tracking_number"
            parameters = [{"name": "@tracking_number", "value": tracking_number}]

            items = []
            async for item in parcels_container.query_items(query=query, parameters=parameters):
                items.append(item)

            if not items:
                return {"found": False, "message": f"No parcel found with tracking number: {tracking_number}"}

            parcel = items[0]

            # Get tracking events
            events_container = self.db.database.get_container_client("tracking_events")
            events_query = f"SELECT * FROM c WHERE c.tracking_number = @tracking_number ORDER BY c.timestamp DESC"

            events = []
            async for event in events_container.query_items(query=events_query, parameters=parameters):
                events.append(event)

            return {
                "found": True,
                "tracking_number": tracking_number,
                "status": parcel.get("status", "Unknown"),
                "current_location": parcel.get("current_location", "Unknown"),
                "origin": parcel.get("origin", "Unknown"),
                "destination": parcel.get("destination", "Unknown"),
                "recipient": parcel.get("recipient_name", "Unknown"),
                "estimated_delivery": parcel.get("estimated_delivery"),
                "weight": parcel.get("weight"),
                "dimensions": parcel.get("dimensions"),
                "last_update": events[0].get("timestamp") if events else None,
                "recent_events": events[:5] if events else [],
            }

        except Exception as e:
            return {"found": False, "error": str(e), "message": f"Error tracking parcel: {str(e)}"}

    async def check_frauds(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent fraud reports

        Args:
            limit: Maximum number of fraud reports to return

        Returns:
            List of fraud reports
        """
        try:
            suspicious_container = self.db.database.get_container_client("suspicious_messages")

            query = "SELECT * FROM c ORDER BY c.timestamp DESC OFFSET 0 LIMIT @limit"
            parameters = [{"name": "@limit", "value": limit}]

            frauds = []
            async for fraud in suspicious_container.query_items(query=query, parameters=parameters):
                frauds.append(fraud)

            return frauds

        except Exception as e:
            return []

    async def get_parcel_location_status(self, tracking_number: str) -> Dict[str, Any]:
        """
        Determine if parcel is in transit or at distribution center

        Args:
            tracking_number: The parcel tracking number

        Returns:
            Location status with detailed information
        """
        parcel_info = await self.track_parcel(tracking_number)

        if not parcel_info.get("found"):
            return parcel_info

        status = parcel_info.get("status", "").lower()
        location = parcel_info.get("current_location", "").lower()

        # Determine location type
        if "transit" in status or "on the way" in status or "picked up" in status:
            location_type = "IN_TRANSIT"
            description = "Parcel is currently in transit"
        elif "distribution" in location or "depot" in location or "facility" in location or "center" in location:
            location_type = "AT_DISTRIBUTION_CENTER"
            description = f'Parcel is at distribution center: {parcel_info.get("current_location")}'
        elif "delivered" in status:
            location_type = "DELIVERED"
            description = "Parcel has been delivered"
        elif "pending" in status or "registered" in status:
            location_type = "AWAITING_PICKUP"
            description = "Parcel is awaiting pickup from sender"
        else:
            location_type = "UNKNOWN"
            description = f"Location status: {status}"

        return {**parcel_info, "location_type": location_type, "location_description": description}

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []

    def get_history(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        return self.conversation_history
