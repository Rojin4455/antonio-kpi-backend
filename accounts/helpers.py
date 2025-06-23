from data_management.models import Contact,Opportunity
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware, now, is_naive
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from data_management.models import Pipeline, PipelineStage
import pytz

logger = logging.getLogger('data_management.helpers')



def create_or_update_contact(contact_data: Dict[str, Any]) -> Optional[Contact]:
    """
    Create or update a contact based on webhook data.
    
    Args:
        contact_data (dict): Contact data from GHL API
        
    Returns:
        Contact instance or None
    """
    if not contact_data:
        logger.warning("No contact data provided")
        return None
        
    contact_id = contact_data.get("id")
    if not contact_id:
        logger.warning("No contact ID in data")
        return None
    
    try:
        # Parse and handle date
        date_added = _parse_date(contact_data.get("dateAdded"))
        
        # Prepare contact data
        contact_data_dict = {
            'contact_id': contact_id,
            'first_name': (contact_data.get("firstName") or "").strip()[:100],
            'last_name': (contact_data.get("lastName") or "").strip()[:100],
            'phone': (contact_data.get("phone") or "").strip()[:20],
            'email': (contact_data.get("email") or "").strip() or None,
            'address': (contact_data.get("address") or "").strip()[:255],
            'country': (contact_data.get("country") or "").strip()[:10],
            'date_added': date_added or now(),
            'date_updated': now(),
            'tags': contact_data.get("tags", []),
            'source': (contact_data.get("source") or "ghl_api").strip()[:100],
        }
        
        # Generate full_name_lowercase
        full_name = f"{contact_data_dict['first_name']} {contact_data_dict['last_name']}"
        contact_data_dict['full_name_lowercase'] = full_name.lower().strip()
        
        # Create or update contact
        contact, created = Contact.objects.update_or_create(
            contact_id=contact_id,
            defaults=contact_data_dict
        )
        
        action = "created" if created else "updated"
        logger.info(f"Contact {contact_id} {action} successfully")
        return contact
        
    except Exception as e:
        logger.error(f"Error creating/updating contact {contact_id}: {e}")
        return None


def create_opportunity(opportunity_data: Dict[str, Any]) -> Optional[Opportunity]:
    """
    Create a new opportunity based on webhook data.
    
    Args:
        opportunity_data (dict): Opportunity data from GHL API
        
    Returns:
        Opportunity instance or None
    """
    if not opportunity_data:
        logger.warning("No opportunity data provided")
        return None
        
    opportunity_id = opportunity_data.get("id")
    if not opportunity_id:
        logger.warning("No opportunity ID in data")
        return None
    
    try:
        # Find related objects
        contact_id = opportunity_data.get("contactId")
        pipeline_id = opportunity_data.get("pipelineId")
        stage_id = opportunity_data.get("pipelineStageId")
        
        contact = Contact.objects.filter(contact_id=contact_id).first() if contact_id else None
        pipeline = Pipeline.objects.filter(pipeline_id=pipeline_id).first() if pipeline_id else None
        stage = PipelineStage.objects.filter(pipeline_stage_id=stage_id).first() if stage_id else None
        
        if not contact:
            logger.warning(f"Contact {contact_id} not found for opportunity {opportunity_id}")
            return None
        
        # Parse dates
        created_timestamp = _parse_date(opportunity_data.get("createdAt")) or now()
        
        # Prepare opportunity data
        opportunity_data_dict = {
            'opportunity_id': opportunity_id,
            'contact': contact,
            'pipeline': pipeline,
            'current_stage': stage,
            'created_by_source': (opportunity_data.get("source") or "ghl_api").strip()[:50],
            'created_by_channel': "ghl_api",
            'source_id': (opportunity_data.get("source") or "").strip()[:255],
            'created_timestamp': created_timestamp,
            'value': _safe_float(opportunity_data.get("monetaryValue")),
            'assigned': (opportunity_data.get("assignedTo") or "").strip()[:150],
            'tags': str(opportunity_data.get("tags", [])),
            'engagement_score': _safe_int(opportunity_data.get("engagementScore")),
            'status': (opportunity_data.get("status") or "").strip()[:50] if opportunity_data.get("status") else None,
            'description': (opportunity_data.get("name") or "").strip(),
            'address': (opportunity_data.get("address") or "").strip(),
        }
        
        # Create opportunity
        opportunity = Opportunity.objects.create(**opportunity_data_dict)
        logger.info(f"Opportunity {opportunity_id} created successfully")
        return opportunity
        
    except Exception as e:
        logger.error(f"Error creating opportunity {opportunity_id}: {e}")
        return None


def update_opportunity(opportunity_data: Dict[str, Any]) -> Optional[Opportunity]:
    """
    Update an existing opportunity based on webhook data.
    
    Args:
        opportunity_data (dict): Opportunity data from GHL API
        
    Returns:
        Opportunity instance or None
    """
    if not opportunity_data:
        logger.warning("No opportunity data provided")
        return None
        
    opportunity_id = opportunity_data.get("id")
    if not opportunity_id:
        logger.warning("No opportunity ID in data")
        return None
    
    try:
        # Get existing opportunity
        opportunity = Opportunity.objects.filter(opportunity_id=opportunity_id).first()
        if not opportunity:
            logger.warning(f"Opportunity {opportunity_id} not found for update")
            return None
        
        # Find related objects
        contact_id = opportunity_data.get("contactId")
        pipeline_id = opportunity_data.get("pipelineId")
        stage_id = opportunity_data.get("pipelineStageId")
        
        contact = Contact.objects.filter(contact_id=contact_id).first() if contact_id else None
        pipeline = Pipeline.objects.filter(pipeline_id=pipeline_id).first() if pipeline_id else None
        stage = PipelineStage.objects.filter(pipeline_stage_id=stage_id).first() if stage_id else None
        
        if not contact:
            logger.warning(f"Contact {contact_id} not found for opportunity {opportunity_id}")
            return None
        
        # Parse dates
        created_timestamp = _parse_date(opportunity_data.get("createdAt")) or opportunity.created_timestamp
        
        # Update opportunity fields
        opportunity.contact = contact
        opportunity.pipeline = pipeline
        opportunity.current_stage = stage
        opportunity.created_by_source = (opportunity_data.get("source") or "ghl_api").strip()[:50]
        opportunity.created_by_channel = "ghl_api"
        opportunity.source_id = (opportunity_data.get("source") or "").strip()[:255]
        opportunity.created_timestamp = created_timestamp
        opportunity.value = _safe_float(opportunity_data.get("monetaryValue"))
        opportunity.assigned = (opportunity_data.get("assignedTo") or "").strip()[:150]
        opportunity.tags = str(opportunity_data.get("tags", []))
        opportunity.engagement_score = _safe_int(opportunity_data.get("engagementScore"))
        opportunity.status = (opportunity_data.get("status") or "").strip()[:50] if opportunity_data.get("status") else None
        opportunity.description = (opportunity_data.get("name") or "").strip()
        opportunity.address = (opportunity_data.get("address") or "").strip()
        
        opportunity.save()
        logger.info(f"Opportunity {opportunity_id} updated successfully")
        return opportunity
        
    except Exception as e:
        logger.error(f"Error updating opportunity {opportunity_id}: {e}")
        return None


def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string and return datetime in 'Australia/Sydney' timezone.

        Args:
            date_str: Date string from API

        Returns:
            Parsed timezone-aware datetime or None
        """
        AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")

        if not date_str:
            return None

        try:
            parsed_date = parse_datetime(date_str)
            if parsed_date:
                if is_naive(parsed_date):
                    parsed_date = make_aware(parsed_date)
                # Convert to Australia/Sydney timezone
                parsed_date = parsed_date.astimezone(AUSTRALIA_SYDNEY_TZ)
                return parsed_date
        except Exception:
            pass

        return None


def _safe_float(value: Any) -> Optional[float]:
    """Safely convert value to float."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value: Any) -> int:
    """Safely convert value to int."""
    if value is None or value == "":
        return 0
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0
    



