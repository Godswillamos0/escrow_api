import httpx
from fastapi import HTTPException
from pydantic import BaseModel
from core.config import PAYSTACK_SECRET, PAYSTACK_BASE_URL



PAYSTACK_SECRET = PAYSTACK_SECRET
PAYSTACK_BASE_URL = PAYSTACK_BASE_URL

headers = {
    "Authorization": f"Bearer {PAYSTACK_SECRET}",
    "Content-Type": "application/json"
}


# ---------- SCHEMA ----------
class TransferRequest(BaseModel):
    bank_code: str          # e.g. "50211" for Kuda Bank
    account_number: str     # e.g. "2017315632"
    account_name: str       # optional, you can pass None
    amount: int             # in kobo (₦5,000 = 500000)
    reason: str


# ---------- CREATE RECIPIENT ----------
async def create_recipient(bank_code: str, account_number: str, name: str):
    url = f"{PAYSTACK_BASE_URL}/transferrecipient"
    payload = {
        "type": "nuban",
        "name": name,
        "account_number": account_number,
        "bank_code": bank_code,
        "currency": "NGN"
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        data = response.json()

        if not data.get("status"):
            raise HTTPException(status_code=400, detail=data.get("message"))

        return data["data"]["recipient_code"]


# ---------- INITIATE TRANSFER ----------
async def initiate_transfer(amount: int, reason: str, recipient_code: str):
    url = f"{PAYSTACK_BASE_URL}/transfer"
    payload = {
        "source": "balance",
        "amount": amount,
        "reason": reason,
        "recipient": recipient_code
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        data = response.json()

        if not data.get("status"):
            raise HTTPException(status_code=400, detail=data.get("message"))

        return data