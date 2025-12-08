"""
Customer Service AI Chatbot
Provides AI-powered assistance for customer service representatives
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from azure_ai_agents import customer_service_agent

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
        # Build enhanced query with context
        enhanced_query = self._build_enhanced_query(query, context)
        
        # Add to conversation history
        self.conversation_history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'query': query,
            'context': context
        })
        
        # Call AI agent
        response = await customer_service_agent({
            'customer_name': context.get('customer_name', 'Customer') if context else 'Customer',
            'issue_type': 'inquiry',
            'tracking_number': context.get('tracking_number') if context else None,
            'details': enhanced_query,
            'preferred_resolution': context.get('preferred_resolution') if context else None
        })
        
        # Add response to history
        self.conversation_history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'response': response
        })
        
        return response
    
    def _build_enhanced_query(self, query: str, context: Dict[str, Any] = None) -> str:
        """Build enhanced query with context"""
        parts = [query]
        
        if context:
            if context.get('tracking_number'):
                parts.append(f"\nTracking Number: {context['tracking_number']}")
            if context.get('customer_name'):
                parts.append(f"Customer: {context['customer_name']}")
            if context.get('additional_info'):
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
            parcels_container = await self.db.get_container("parcels")
            
            query = f"SELECT * FROM c WHERE c.tracking_number = @tracking_number"
            parameters = [{"name": "@tracking_number", "value": tracking_number}]
            
            items = []
            async for item in parcels_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ):
                items.append(item)
            
            if not items:
                return {
                    'found': False,
                    'message': f'No parcel found with tracking number: {tracking_number}'
                }
            
            parcel = items[0]
            
            # Get tracking events
            events_container = await self.db.get_container("tracking_events")
            events_query = f"SELECT * FROM c WHERE c.tracking_number = @tracking_number ORDER BY c.timestamp DESC"
            
            events = []
            async for event in events_container.query_items(
                query=events_query,
                parameters=parameters,
                enable_cross_partition_query=True
            ):
                events.append(event)
            
            return {
                'found': True,
                'tracking_number': tracking_number,
                'status': parcel.get('status', 'Unknown'),
                'current_location': parcel.get('current_location', 'Unknown'),
                'origin': parcel.get('origin', 'Unknown'),
                'destination': parcel.get('destination', 'Unknown'),
                'recipient': parcel.get('recipient_name', 'Unknown'),
                'estimated_delivery': parcel.get('estimated_delivery'),
                'weight': parcel.get('weight'),
                'dimensions': parcel.get('dimensions'),
                'last_update': events[0].get('timestamp') if events else None,
                'recent_events': events[:5] if events else []
            }
            
        except Exception as e:
            return {
                'found': False,
                'error': str(e),
                'message': f'Error tracking parcel: {str(e)}'
            }
    
    async def check_frauds(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent fraud reports
        
        Args:
            limit: Maximum number of fraud reports to return
            
        Returns:
            List of fraud reports
        """
        try:
            suspicious_container = await self.db.get_container("suspicious_messages")
            
            query = "SELECT * FROM c ORDER BY c.timestamp DESC OFFSET 0 LIMIT @limit"
            parameters = [{"name": "@limit", "value": limit}]
            
            frauds = []
            async for fraud in suspicious_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ):
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
        
        if not parcel_info.get('found'):
            return parcel_info
        
        status = parcel_info.get('status', '').lower()
        location = parcel_info.get('current_location', '').lower()
        
        # Determine location type
        if 'transit' in status or 'on the way' in status or 'picked up' in status:
            location_type = 'IN_TRANSIT'
            description = 'Parcel is currently in transit'
        elif 'distribution' in location or 'depot' in location or 'facility' in location or 'center' in location:
            location_type = 'AT_DISTRIBUTION_CENTER'
            description = f'Parcel is at distribution center: {parcel_info.get("current_location")}'
        elif 'delivered' in status:
            location_type = 'DELIVERED'
            description = 'Parcel has been delivered'
        elif 'pending' in status or 'registered' in status:
            location_type = 'AWAITING_PICKUP'
            description = 'Parcel is awaiting pickup from sender'
        else:
            location_type = 'UNKNOWN'
            description = f'Location status: {status}'
        
        return {
            **parcel_info,
            'location_type': location_type,
            'location_description': description
        }
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        return self.conversation_history
