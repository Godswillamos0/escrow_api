import httpx
from core.config import PAYSTACK_SECRET, PAYSTACK_BASE_URL

PAYSTACK_SECRET = PAYSTACK_SECRET

async def fetch_banks() -> dict:
    url = f"{PAYSTACK_BASE_URL}/bank"
    headers = {"Authorization": f"Bearer ${PAYSTACK_SECRET}"}

    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers)

        print("Status Code:", r.status_code)
        print("Raw Response:", r.text)  # <-- IMPORTANT

        r.raise_for_status()
        return r.json()
     
    
async def resolve_bank_account(account_number: str, bank_code: str) -> dict | None:
    url = f"{PAYSTACK_BASE_URL}/bank/resolve"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET}",
        "Content-Type": "application/json"
    }
    params = {
        "account_number": account_number,
        "bank_code": bank_code
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            return data.get("data")
        else:
            '''print(f"Error resolving bank account: {response.text}")
            print(response.status_code)'''
            return None
    
    
async def get_all_banks_from_paystack() -> dict:
    banks = await fetch_banks()
    
    return [
        {
         "bank_code": bank_detail["code"],
         "name": bank_detail["name"],
         "slug": bank_detail["slug"]
         }
        for bank_detail in banks["data"]
            ]
    