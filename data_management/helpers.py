import requests
import time
from typing import List, Dict, Any, Optional
from django.utils.dateparse import parse_datetime
from django.db import transaction
from django.utils.timezone import make_aware, now, is_naive
from datetime import datetime
from data_management.models import Contact, Pipeline, PipelineStage, Opportunity
from accounts.models import GHLAuthCredentials
import logging
import pytz

# logger = logging.getLogger(__name__)

logger = logging.getLogger('data_management.helpers')


class GHLSyncService:
    """
    Service class to handle automated synchronization of contacts and opportunities
    from GoHighLevel API to local Django models.
    """
    
    def __init__(self, location_id: str, access_token: str = None):
        self.location_id = location_id
        self.access_token = access_token
        self.base_url = "https://services.leadconnectorhq.com"
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "Version": "2021-07-28"
        }
    
    def sync_all_data(self):
        """
        Main method to sync all contacts and opportunities from GHL.
        """
        logger.info("Starting full GHL data synchronization...")
        
        try:
            # First, sync contacts
            contacts = self.fetch_all_contacts()
            self.sync_contacts_to_db(contacts)
            
            # Then, sync opportunities
            opportunities = self.fetch_all_opportunities()
            self.sync_opportunities_to_db(opportunities)
            
            logger.info("GHL data synchronization completed successfully!")
            
        except Exception as e:
            logger.error(f"Error during GHL synchronization: {e}")
            raise

    def fetch_all_contacts(self) -> List[Dict[str, Any]]:
        """
        Fetch all contacts from GoHighLevel API with proper pagination handling.
        
        Returns:
            List[Dict]: List of all contacts
        """
        endpoint = f"{self.base_url}/contacts/"
        all_contacts = []
        start_after = None
        start_after_id = None
        page_count = 0
        
        while True:
            page_count += 1
            logger.info(f"Fetching contacts page {page_count}...")
            
            # Set up parameters for current request
            params = {
                "locationId": self.location_id,
                "limit": 100,  # Maximum allowed by API
            }
            
            # Add pagination parameters if available
            if start_after:
                params["startAfter"] = start_after
            if start_after_id:
                params["startAfterId"] = start_after_id
                
            try:
                response = requests.get(endpoint, headers=self.headers, params=params)
                
                if response.status_code != 200:
                    logger.error(f"Error Response: {response.status_code} - {response.text}")
                    raise Exception(f"API Error: {response.status_code}, {response.text}")
                
                data = response.json()
                contacts = data.get("contacts", [])
                
                if not contacts:
                    logger.info("No more contacts found.")
                    break
                    
                all_contacts.extend(contacts)
                logger.info(f"Retrieved {len(contacts)} contacts. Total so far: {len(all_contacts)}")
                
                # Update pagination cursors for next request
                if contacts:
                    last_contact = contacts[-1]
                    start_after_id = last_contact.get("id")
                    start_after = self._extract_timestamp(last_contact)
                
                # Check if we've reached the end
                meta = data.get("meta", {})
                total_count = meta.get("total", 0)
                if total_count > 0 and len(all_contacts) >= total_count:
                    logger.info(f"Retrieved all {total_count} contacts.")
                    break
                    
                # If we got fewer contacts than the limit, we're likely at the end
                if len(contacts) < 100:
                    logger.info("Retrieved fewer contacts than limit, likely at end.")
                    break
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise
                
            # Add a small delay to be respectful to the API
            time.sleep(0.1)
            
            # Safety check to prevent infinite loops
            if page_count > 1000:
                logger.warning("Stopped after 1000 pages to prevent infinite loop")
                break
        
        logger.info(f"Total contacts retrieved: {len(all_contacts)}")
        return all_contacts

    def fetch_all_opportunities(self) -> List[Dict[str, Any]]:
        """
        Fetch all opportunities from GoHighLevel API with proper pagination handling.
        
        Returns:
            List[Dict]: List of all opportunities
        """
        endpoint = f"{self.base_url}/opportunities/search/"
        all_opportunities = []
        start_after = None
        start_after_id = None
        page_count = 0
        
        while True:
            page_count += 1
            logger.info(f"Fetching opportunities page {page_count}...")
            
            # Set up parameters for current request
            params = {
                "location_id": self.location_id,
                "limit": 100,  # Maximum allowed by API
            }
            
            # Add pagination parameters if available
            if start_after:
                params["startAfter"] = start_after
            if start_after_id:
                params["startAfterId"] = start_after_id
                
            try:
                response = requests.get(endpoint, headers=self.headers, params=params)
                
                if response.status_code != 200:
                    logger.error(f"Error Response: {response.status_code} - {response.text}")
                    raise Exception(f"API Error: {response.status_code}, {response.text}")
                
                data = response.json()
                opportunities = data.get("opportunities", [])
                
                if not opportunities:
                    logger.info("No more opportunities found.")
                    break
                    
                all_opportunities.extend(opportunities)
                logger.info(f"Retrieved {len(opportunities)} opportunities. Total so far: {len(all_opportunities)}")
                
                # Update pagination cursors for next request
                if opportunities:
                    last_opportunity = opportunities[-1]
                    start_after_id = last_opportunity.get("id")
                    start_after = self._extract_timestamp(last_opportunity)
                
                # Check if we've reached the end
                meta = data.get("meta", {})
                total_count = meta.get("total", 0)
                if total_count > 0 and len(all_opportunities) >= total_count:
                    logger.info(f"Retrieved all {total_count} opportunities.")
                    break
                    
                # If we got fewer opportunities than the limit, we're likely at the end
                if len(opportunities) < 100:
                    logger.info("Retrieved fewer opportunities than limit, likely at end.")
                    break
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise
                
            # Add a small delay to be respectful to the API
            time.sleep(0.1)
            
            # Safety check to prevent infinite loops
            if page_count > 1000:
                logger.warning("Stopped after 1000 pages to prevent infinite loop")
                break
        
        logger.info(f"Total opportunities retrieved: {len(all_opportunities)}")
        return all_opportunities

    def sync_contacts_to_db(self, contact_data: List[Dict[str, Any]]):
        """
        Syncs contact data from API into the local Contact model using bulk operations.
        
        Args:
            contact_data (list): List of contact dicts from GoHighLevel API
        """
        if not contact_data:
            logger.info("No contact data to sync.")
            return
            
        logger.info(f"Syncing {len(contact_data)} contacts to database...")
        
        contacts_to_create = []
        contacts_to_update = []
        
        # Get existing contact IDs for efficient lookups
        existing_contacts = {
            contact.contact_id: contact 
            for contact in Contact.objects.filter(
                contact_id__in=[c.get('id') for c in contact_data if c.get('id')]
            ).select_related()
        }

        for item in contact_data:
            contact_id = item.get("id")
            if not contact_id:
                continue
                
            # Parse and handle date
            date_added = self._parse_date(item.get("createdAt"))
            
            # Prepare contact data
            contact_data_dict = {
                'contact_id': contact_id,
                'first_name': (item.get("firstName") or "").strip()[:100],
                'last_name': (item.get("lastName") or "").strip()[:100],
                'phone': (item.get("phone") or "").strip()[:20],
                'email': (item.get("email") or "").strip() or None,
                'address': (item.get("address") or "").strip()[:255],
                'country': (item.get("country") or "").strip()[:10],
                'date_added': date_added or now(),
                'date_updated': now(),
                'tags': item.get("tags", []),
                'source': (item.get("source") or "ghl_api").strip()[:100],
            }
            
            # Generate full_name_lowercase
            full_name = f"{contact_data_dict['first_name']} {contact_data_dict['last_name']}"
            contact_data_dict['full_name_lowercase'] = full_name.lower().strip()

            if contact_id in existing_contacts:
                # Update existing contact
                existing_contact = existing_contacts[contact_id]
                for key, value in contact_data_dict.items():
                    if key != 'contact_id':  # Don't update the ID
                        setattr(existing_contact, key, value)
                contacts_to_update.append(existing_contact)
            else:
                # Create new contact
                contacts_to_create.append(Contact(**contact_data_dict))

        # Perform bulk operations
        with transaction.atomic():
            if contacts_to_create:
                Contact.objects.bulk_create(contacts_to_create, ignore_conflicts=True)
                logger.info(f"Created {len(contacts_to_create)} new contacts.")
            
            if contacts_to_update:
                # Bulk update existing contacts
                Contact.objects.bulk_update(
                    contacts_to_update,
                    ['first_name', 'last_name', 'phone', 'email', 'address', 
                     'country', 'date_added', 'date_updated', 'tags', 'source', 
                     'full_name_lowercase']
                )
                logger.info(f"Updated {len(contacts_to_update)} existing contacts.")

    def sync_opportunities_to_db(self, opportunity_data: List[Dict[str, Any]]):
        """
        Syncs opportunity data from API into the local Opportunity model.
        
        Args:
            opportunity_data (list): List of opportunity dicts from GoHighLevel API
        """
        if not opportunity_data:
            logger.info("No opportunity data to sync.")
            return
            
        logger.info(f"Syncing {len(opportunity_data)} opportunities to database...")
        
        opportunities_to_create = []
        opportunities_to_update = []
        
        # Get existing opportunities for efficient lookups
        existing_opportunities = {
            opp.opportunity_id: opp 
            for opp in Opportunity.objects.filter(
                opportunity_id__in=[o.get('id') for o in opportunity_data if o.get('id')]
            ).select_related('contact', 'pipeline', 'current_stage')
        }

        
        
        # Preload contacts, pipelines, and stages for efficient lookups
        contact_lookup = {
            contact.contact_id: contact 
            for contact in Contact.objects.all()
        }
        pipeline_lookup = {
            pipeline.pipeline_id: pipeline 
            for pipeline in Pipeline.objects.all()
        }
        stage_lookup = {
            stage.pipeline_stage_id: stage 
            for stage in PipelineStage.objects.all()
        }

        for item in opportunity_data:
            opportunity_id = item.get("id")
            if not opportunity_id:
                continue
                
            # Find related objects
            contact_id = item.get("contactId")
            pipeline_id = item.get("pipelineId")
            stage_id = item.get("pipelineStageId")
            
            contact = contact_lookup.get(contact_id)
            pipeline = pipeline_lookup.get(pipeline_id)
            stage = stage_lookup.get(stage_id)
            
            if not contact:
                logger.warning(f"Contact {contact_id} not found for opportunity {opportunity_id}")
                continue
                
            # Parse dates
            created_timestamp = self._parse_date(item.get("createdAt")) or now()
            
            # Prepare opportunity data
            opportunity_data_dict = {
                'opportunity_id': opportunity_id,
                'contact': contact,
                'pipeline': pipeline,
                'current_stage': stage,
                'created_by_source': (item.get("source") or "ghl_api").strip()[:50],
                'created_by_channel': "ghl_api",
                'source_id': (item.get("source") or "").strip()[:255],
                'created_timestamp': created_timestamp,
                'value': self._safe_float(item.get("monetaryValue")),
                'assigned': (item.get("assignedTo") or "").strip()[:150],
                'tags': str(item.get("tags", [])),
                'engagement_score': self._safe_int(item.get("engagementScore")),
                'status': (item.get("status") or "").strip()[:50] if item.get("status") else None,
                'description': (item.get("name") or "").strip(),
                'address': (item.get("address") or "").strip(),
            }

            if opportunity_id in existing_opportunities:
                # Update existing opportunity
                existing_opportunity = existing_opportunities[opportunity_id]
                for key, value in opportunity_data_dict.items():
                    if key != 'opportunity_id':  # Don't update the ID
                        setattr(existing_opportunity, key, value)
                opportunities_to_update.append(existing_opportunity)
            else:
                # Create new opportunity
                opportunities_to_create.append(Opportunity(**opportunity_data_dict))

        # Perform bulk operations
        with transaction.atomic():
            if opportunities_to_create:
                Opportunity.objects.bulk_create(opportunities_to_create, ignore_conflicts=True)
                logger.info(f"Created {len(opportunities_to_create)} new opportunities.")
            
            if opportunities_to_update:
                # Bulk update existing opportunities
                Opportunity.objects.bulk_update(
                    opportunities_to_update,
                    ['contact', 'pipeline', 'current_stage', 'created_by_source', 
                     'created_by_channel', 'source_id', 'created_timestamp', 'value', 
                     'assigned', 'tags', 'engagement_score', 'status', 'description', 'address']
                )
                logger.info(f"Updated {len(opportunities_to_update)} existing opportunities.")

    def _extract_timestamp(self, record: Dict[str, Any]) -> Optional[int]:
        """
        Extract timestamp from a record for pagination purposes.
        
        Args:
            record: API record containing date information
            
        Returns:
            Timestamp in milliseconds or None
        """
        for field in ["dateAdded", "createdAt", "updatedAt"]:
            date_value = record.get(field)
            if date_value:
                if isinstance(date_value, str):
                    try:
                        dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                        return int(dt.timestamp() * 1000)
                    except:
                        try:
                            return int(float(date_value))
                        except:
                            continue
                elif isinstance(date_value, (int, float)):
                    return int(date_value)
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

    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _safe_int(self, value: Any) -> int:
        """Safely convert value to int."""
        if value is None or value == "":
            return 0
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return 0


# Convenience functions for easy usage
def sync_ghl_contacts_and_opportunities(location_id: str, access_token: str = None):
    """
    Main function to sync all contacts and opportunities from GHL.
    
    Args:
        location_id (str): GHL location ID
        access_token (str): GHL API access token
    """
    if not access_token:
        # Try to get from credentials model if not provided
        try:
            credentials = GHLAuthCredentials.objects.first()
            if credentials:
                access_token = credentials.access_token
            else:
                raise ValueError("No access token provided and no credentials found in database")
        except Exception as e:
            raise ValueError(f"Could not retrieve access token: {e}")
    
    print("location_id:", location_id)
    
    sync_service = GHLSyncService(location_id, access_token)
    sync_service.sync_all_data()


def sync_ghl_contacts_only(location_id: str, access_token: str = None):
    """
    Function to sync only contacts from GHL.
    
    Args:
        location_id (str): GHL location ID
        access_token (str): GHL API access token
    """
    if not access_token:
        try:
            credentials = GHLAuthCredentials.objects.first()
            if credentials:
                access_token = credentials.access_token
            else:
                raise ValueError("No access token provided and no credentials found in database")
        except Exception as e:
            raise ValueError(f"Could not retrieve access token: {e}")
    
    sync_service = GHLSyncService(location_id, access_token)
    contacts = sync_service.fetch_all_contacts()
    sync_service.sync_contacts_to_db(contacts)


def sync_ghl_opportunities_only(location_id: str, access_token: str = None):
    """
    Function to sync only opportunities from GHL.
    
    Args:
        location_id (str): GHL location ID
        access_token (str): GHL API access token
    """
    if not access_token:
        try:
            credentials = GHLAuthCredentials.objects.first()
            if credentials:
                access_token = credentials.access_token
            else:
                raise ValueError("No access token provided and no credentials found in database")
        except Exception as e:
            raise ValueError(f"Could not retrieve access token: {e}")
    
    sync_service = GHLSyncService(location_id, access_token)
    opportunities = sync_service.fetch_all_opportunities()
    sync_service.sync_opportunities_to_db(opportunities)