import requests
import uuid

# Wise API Configurations
WISE_API_KEY = "b16c85fe-0bca-47d8-ae35-66df206616a5"
WISE_BASE_URL = "https://api.sandbox.transferwise.tech"  # Use "https://api.wise.com/v1" for live

def get_profile_id():
    """Fetch Wise Profile ID."""
    url = f"{WISE_BASE_URL}/profiles"
    headers = {"Authorization": f"Bearer {WISE_API_KEY}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        profiles = response.json()
        return profiles[0]["id"] if profiles else None  # Return first profile ID
    return None

def create_virtual_card():
    """Generate a Wise Virtual Card for making payments."""
    profile_id = "28706180"  # Get the profile ID dynamically
    if not profile_id:
        return {"error": "Failed to retrieve Wise Profile ID"}
    
    url = f"{WISE_BASE_URL}/v3/spend/profiles/{profile_id}/card-orders"

    headers = {
        "Authorization": f"Bearer {WISE_API_KEY}",
        "Content-Type": "application/json",
        "X-idempotence-uuid": str(uuid.uuid4())
    }

    payload = {
        "program": "VISA_DEBIT_BUSINESS_UK_1_VIRTUAL_CARDS_API",
        "cardHolderName": "Graham Ramirez",
        "cardType": "VIRTUAL",
        "address": {
            "firstLine": "23 Ashford Ridgeway",
            "secondLine": None,
            "thirdLine": None,
            "city": "Faisawdul Lake",
            "postalCode": "E77JJ",
            "state": None,
            "country": "Spain"
        },
        "deliveryOption": "POSTAL_SERVICE_STANDARD"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        return response.json()  # Successfully return the response data

    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {e}"}  # Return error message if request fails

def get_wise_balance():
    """Fetch Wise account balance and display it as a Virtual Wallet."""
    profile_id = "28706180"  # Get the profile ID dynamically
    print(profile_id)
    if not profile_id:
        return {"error": "Failed to retrieve Wise Profile ID"}

    url = f"{WISE_BASE_URL}/v4/profiles/{profile_id}/balances?types=STANDARD"
    headers = {"Authorization": f"Bearer {WISE_API_KEY}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        accounts = response.json()

        # Extract balances for all currencies
        balance_summary = {acc["currency"]: acc["amount"]["value"] for acc in accounts}
        return {"virtual_wallet": balance_summary}
    else:
        return {"error": "Failed to fetch balance"}

def fetch_exchange_rate(from_currency, to_currency):
    """Fetch the real-time exchange rate from Wise."""
    url = f"{WISE_BASE_URL}/v1/rates?source={from_currency}&target={to_currency}"
    headers = {"Authorization": f"Bearer {WISE_API_KEY}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        rates = response.json()
        return {"exchange_rate": rates[0]["rate"], "date": rates[0]["time"]}
    else:
        return {"error": "Failed to fetch exchange rate"}

def create_quote(from_currency, to_currency, amount):
    """Create a quote for currency exchange."""
    profile_id = "28706180"  # Get the profile ID dynamically
    if not profile_id:
        return {"error": "Failed to retrieve Wise Profile ID"}

    url = f"{WISE_BASE_URL}/v3/profiles/{profile_id}/quotes"
    headers = {"Authorization": f"Bearer {WISE_API_KEY}", "Content-Type": "application/json"}

    payload = {
        "profile": profile_id,
        "source": from_currency,
        "target": to_currency,
        "rateType": "FIXED",
        "sourceAmount": amount,  # Amount to exchange
        "payOut": "BALANCE"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        quote = response.json()

        # Extract relevant details from quote
        filtered_data = {
            "quote_id": quote.get("id"),
            "from_currency": quote.get("sourceCurrency"),
            "to_currency": quote.get("targetCurrency"),
            "source_amount": quote.get("sourceAmount"),
            "rate": quote.get("rate"),
            "fee": quote.get("pricingConfiguration", {}).get("fee", {}).get("fixed", 0),
            "discount": quote.get("paymentOptions", [{}])[0].get("fee", {}).get("discount", 0),
            "final_amount": quote.get("paymentOptions", [{}])[0].get("targetAmount")
        }
        return filtered_data
    else:
        return {"error": "Failed to create quote", "status_code": response.status_code, "message": response.text}

def get_balance_id(currency):
    """Retrieve balance ID for a given currency."""
    profile_id = "28706180" # Get the profile ID dynamically
    if not profile_id:
        return {"error": "Failed to retrieve Wise Profile ID"}

    url = f"{WISE_BASE_URL}/v4/profiles/{profile_id}/balances?types=STANDARD"
    headers = {"Authorization": f"Bearer {WISE_API_KEY}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        balances = response.json()

        for balance in balances:
            if balance.get("currency") == currency:
                return balance.get("id")  # Safe retrieval of balance ID

    return None  # No balance found for the currency

