import requests
from celery import shared_task
from accounts.models import GHLAuthCredentials
from django.conf import settings
from data_management.helpers import sync_ghl_contacts_and_opportunities
from data_management.models import Contact, Opportunity
from accounts.helpers import create_or_update_contact, update_opportunity, create_opportunity
from accounts.services import get_ghl_contact, get_ghl_opportunity

@shared_task
def make_api_for_ghl():
    print("api called") 
    credentials = GHLAuthCredentials.objects.first()
    
    print("credentials tokenL", credentials)
    refresh_token = credentials.refresh_token

    
    response = requests.post('https://services.leadconnectorhq.com/oauth/token', data={
        'grant_type': 'refresh_token',
        'client_id': settings.GHL_CLIENT_ID,
        'client_secret': settings.GHL_CLIENT_SECRET,
        'refresh_token': refresh_token
    })
    
    new_tokens = response.json()
    print("newtoken :", new_tokens)

    obj, created = GHLAuthCredentials.objects.update_or_create(
            location_id= new_tokens.get("locationId"),
            defaults={
                "access_token": new_tokens.get("access_token"),
                "refresh_token": new_tokens.get("refresh_token"),
                "expires_in": new_tokens.get("expires_in"),
                "scope": new_tokens.get("scope"),
                "user_type": new_tokens.get("userType"),
                "company_id": new_tokens.get("companyId"),
                "user_id":new_tokens.get("userId"),

            }
        )



@shared_task
def sync_opp__and_cntct_task(location_id, access_token):
    sync_ghl_contacts_and_opportunities(location_id, access_token)




@shared_task
def handle_webhook_event(data, event_type):
    """
    Process webhook events asynchronously.
    Note: Removed 'self' parameter as it's not needed for shared_task
    """
    try:
        # Get access token
        credentials = GHLAuthCredentials.objects.first()
        if not credentials:
            print("No GHL credentials found")
            return
            
        access_token = credentials.access_token
        
        # Handle Contact events
        if event_type in ["ContactCreate", "ContactUpdate"]:
            contact_id = data.get("id")
            if contact_id:
                contact_data = get_ghl_contact(contact_id, access_token)
                contact = contact_data.get("contact")
                if contact:
                    create_or_update_contact(contact)
                else:
                    print(f"Failed to fetch contact data for {contact_id}")
            else:
                print("No contact ID in webhook data")
        
        elif event_type == "ContactDelete":
            contact_id = data.get("id")
            if contact_id:
                contact = Contact.objects.filter(contact_id=contact_id).first()
                if contact:
                    # Delete related opportunities first
                    Opportunity.objects.filter(contact__contact_id=contact_id).delete()
                    contact.delete()
                    print(f"Contact {contact_id} deleted successfully")
                else:
                    print(f"Contact {contact_id} not found for deletion")
            else:
                print("No contact ID in webhook data")

        # Handle Opportunity events
        elif event_type == "OpportunityCreate":
            opportunity_id = data.get("id")
            if opportunity_id:
                opportunity_data = get_ghl_opportunity(opportunity_id, access_token)
                opportunity = opportunity_data.get("opportunity")
                if opportunity:
                    create_opportunity(opportunity)
                else:
                    print(f"Failed to fetch opportunity data for {opportunity_id}")
            else:
                print("No opportunity ID in webhook data")

        elif event_type == "OpportunityUpdate":
            opportunity_id = data.get("id")
            if opportunity_id:
                opportunity_data = get_ghl_opportunity(opportunity_id, access_token)
                opportunity = opportunity_data.get("opportunity")
                if opportunity:
                    update_opportunity(opportunity)
                else:
                    print(f"Failed to fetch opportunity data for {opportunity_id}")
            else:
                print("No opportunity ID in webhook data")

        elif event_type == "OpportunityDelete":
            # Handle different possible data structures for opportunity deletion
            opportunity_id = None
            
            # Try different ways to get opportunity ID based on webhook structure
            if data.get("id"):
                opportunity_id = data.get("id")
            elif data.get("opportunity", {}).get("id"):
                opportunity_id = data.get("opportunity", {}).get("id")
            
            if opportunity_id:
                opportunity = Opportunity.objects.filter(opportunity_id=opportunity_id).first()
                if opportunity:
                    opportunity.delete()
                    print(f"Opportunity {opportunity_id} deleted successfully")
                else:
                    print(f"Opportunity {opportunity_id} not found for deletion")
            else:
                print("No opportunity ID found in webhook data")
        
        else:
            print(f"Unhandled event type: {event_type}")
            
    except Exception as e:
        print(f"Error handling webhook event {event_type}: {e}")
        # You might want to log this to a proper logging system
        import traceback
        print(traceback.format_exc())