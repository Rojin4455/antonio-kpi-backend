import requests
from accounts.models import GHLAuthCredentials
def get_ghl_contact(contactId, access_token):

    url = f"https://services.leadconnectorhq.com/contacts/{contactId}"
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28"
    }
    
    response = requests.get(url, headers=headers)

    
    if response.status_code == 200:
        return response.json()
    else:
        
        return {"error": response.status_code, "message": response.text}
    
def get_ghl_opportunity(oppertunity_id, access_token):
    url = f"https://services.leadconnectorhq.com/opportunities/{oppertunity_id}"
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28"
    }
    
    response = requests.get(url, headers=headers)

    print("response: ", response.json())
    
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.status_code, "message": response.text}
    




def get_location_name(location_id: str, access_token: str) -> str:
    url = f"https://services.leadconnectorhq.com/locations/{location_id}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise exception for HTTP errors

    data = response.json()
    return data.get("location", {}).get("name"),  data.get("location", {}).get("timezone")