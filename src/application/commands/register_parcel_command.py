"""
Register Parcel Command - CQRS Write Operation
"""
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from src.infrastructure.database.repositories import ParcelRepository
from src.infrastructure.agents import parcel_intake_agent
from src.domain.services import ParcelService


class RegisterParcelCommand:
    """Command to register a new parcel with AI validation"""
    
    def __init__(self, parcel_repo: ParcelRepository):
        self.parcel_repo = parcel_repo
    
    async def execute(
        self,
        sender_name: str,
        sender_address: str,
        sender_phone: str,
        recipient_name: str,
        recipient_address: str,
        recipient_phone: str,
        service_type: str = 'standard',
        weight: float = 0.0,
        dimensions: str = '',
        declared_value: float = 0.0,
        special_instructions: str = '',
        store_location: str = 'WebPortal',
        lodgement_photo_base64: Optional[str] = None,
        destination_postcode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute parcel registration with AI validation
        
        Args:
            sender_name: Sender's full name
            sender_address: Sender's address
            sender_phone: Sender's phone
            recipient_name: Recipient's full name
            recipient_address: Recipient's complete address
            recipient_phone: Recipient's phone
            service_type: Service type (express/standard/economy)
            weight: Weight in kg
            dimensions: Dimensions string
            declared_value: Declared value
            special_instructions: Special delivery instructions
            store_location: Lodgement location
            lodgement_photo_base64: Base64 encoded lodgement photo
            destination_postcode: Destination postcode (auto-extracted if not provided)
            
        Returns:
            Registration result with tracking number and validation feedback
        """
        # Generate tracking number and barcode
        tracking_number = f"DT{uuid.uuid4().hex[:10].upper()}"
        barcode = f"BC{uuid.uuid4().hex[:12].upper()}"
        
        # Extract destination postcode if not provided
        if not destination_postcode and recipient_address:
            import re
            postcode_match = re.search(r'\b(\d{4})\b', recipient_address)
            if postcode_match:
                destination_postcode = postcode_match.group(1)
        
        # Determine destination state
        destination_state = ParcelService.get_state_from_postcode(destination_postcode) if destination_postcode else "UNKNOWN"
        
        # Validate with Azure AI Parcel Intake Agent
        parcel_data = {
            'tracking_number': tracking_number,
            'sender_name': sender_name,
            'sender_address': sender_address,
            'recipient_name': recipient_name,
            'recipient_address': recipient_address,
            'destination_postcode': destination_postcode,
            'destination_state': destination_state,
            'service_type': service_type,
            'weight_kg': weight,
            'dimensions': dimensions,
            'declared_value': declared_value,
            'special_instructions': special_instructions,
        }
        
        # Call AI validation
        validation_result = await parcel_intake_agent(parcel_data)
        
        # Register parcel in repository
        parcel = await self.parcel_repo.create(
            barcode=barcode,
            sender_name=sender_name,
            sender_address=sender_address,
            sender_phone=sender_phone,
            recipient_name=recipient_name,
            recipient_address=recipient_address,
            recipient_phone=recipient_phone,
            destination_postcode=destination_postcode,
            destination_state=destination_state,
            service_type=service_type.lower(),
            weight=weight,
            dimensions=dimensions,
            declared_value=declared_value,
            special_instructions=special_instructions,
            store_location=store_location,
            lodgement_photo_base64=lodgement_photo_base64,
        )
        
        return {
            'success': True,
            'tracking_number': tracking_number,
            'barcode': barcode,
            'parcel': parcel,
            'ai_validation': validation_result,
        }
