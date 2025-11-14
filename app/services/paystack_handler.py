from fastapi import Request, HTTPException, status
import hmac
import os
from dotenv import load_dotenv
import hashlib
from fastapi.responses import RedirectResponse
import httpx
from db.models import TransactionStatus, TransactionType, Wallet, WalletTransaction, User
from datetime import datetime
from schemas.wallet import PaymentRequest
from db.dependencies import db_dependency
from utils.mail_config import send_mail
from decimal import Decimal
from core.config import PAYSTACK_SECRET

PAYSTACK_SECRET = PAYSTACK_SECRET

def verify_paystack_signature(request_body: bytes, signature: str) -> bool:
    if not PAYSTACK_SECRET:
        return False
        
    # 1. Compute the hash using HMAC SHA512
    # The request body *must* be the raw bytes received from Paystack
    computed_hmac = hmac.new(
        key=PAYSTACK_SECRET.encode('utf-8'),
        msg=request_body,
        digestmod=hashlib.sha512
    ).hexdigest()
    
    return hmac.compare_digest(computed_hmac, signature)



async def paystack_webhook_handler(request: Request,
                                   db: db_dependency):
    
    paystack_signature = request.headers.get("x-paystack-signature")
    
    if not paystack_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="X-Paystack-Signature header missing."
        )

    raw_body = await request.body()

    # 3. Validate the signature
    if not verify_paystack_signature(raw_body, paystack_signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Signature validation failed. Request may be malicious."
        )


    try:
        # Convert raw body bytes to JSON
        event_payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid JSON payload."
        )
        
    # --- Webhook Processing Logic ---
    event_type = event_payload.get("event")
    
    print(f"Received Paystack event: {event_type}")

    if event_type == "charge.success":
        # Process a successful payment
        transaction_data = event_payload.get("data")
        reference = transaction_data.get("reference")
        email = transaction_data.get("customer", {}).get("email")
        amount = transaction_data.get("amount")
        metadata = transaction_data.get("metadata")
        source_id = metadata.get("source_id")
        username = metadata.get("user_id")
        wallet_id = metadata.get("wallet_id")
        
        # **ACTION:** Update your database
        transaction_model = db.query(WalletTransaction).filter(WalletTransaction.reference_code==reference).first()
        transaction_model.status = TransactionStatus.SUCCESS
        
        # Add to wallet
        wallet_model = db.query(Wallet).filter(Wallet.id==wallet_id).first()
        wallet_model.updated_at = datetime.utcnow()
        wallet_model.balance += Decimal(amount) / Decimal(100)
        db.add(wallet_model)
        
        db.commit()
        
        # send confirmation emails,
        await send_mail(
            email=email,
            subject="Payment Confirmation",
            body= f'''
            You just added funds to your wallet.
            Amount: {amount/100:.2f} 
            Reference: {reference}
            Metadata: {metadata}
            '''
        )
        
        
         
        # fulfill the order, etc., using the reference and amount.
        print(f"✅ Success: Transaction {reference} for {amount/100:.2f} processed.")
        print(email)
    elif event_type == "charge.failed":
        transaction_data = event_payload.get("data")
        reference = transaction_data.get("reference")
        
        # **ACTION:** Update your database
        transaction_model = db.query(WalletTransaction).filter(WalletTransaction.reference_code==reference).first()
        if transaction_model:
            transaction_model.status = TransactionStatus.FAILED
            db.commit()
            
            await send_mail(
            email=email,
            subject="Payment Confirmation",
            body= f'''
            You tried adding funds to your wallet, but it failed.
            Amount: {amount/100:.2f} 
            Reference: {reference}
            Metadata: {metadata}
            '''
        )
        
        # You might want to send a notification to the user
        return {
            "status": "success", 
            "message":f"❌ Failure: Transaction {reference} failed."
        }

    elif event_type == "transfer.success":
        transfer_data = event_payload.get("data")
        reference = transfer_data.get("reference")
        # This confirms a withdrawal was successful.
        # Update your withdrawal transaction status to SUCCESS.
        print(f"✅ Success: Transfer {reference} was successful.")

    elif event_type == "transfer.failed":
        transfer_data = event_payload.get("data")
        reference = transfer_data.get("reference")
        # This indicates a withdrawal failed.
        # You should revert the withdrawal transaction and notify the user.
        print(f"❌ Failure: Transfer {reference} failed.")

    elif event_type == "charge.dispute.create":
        dispute_data = event_payload.get("data")
        reference = dispute_data.get("reference")
        # A customer has disputed a charge.
        # Flag this transaction in your system for investigation.
        print(f"⚠️ Dispute: A chargeback was initiated for transaction {reference}.")
        
    else:
        # Handle other events you care about
        print(f"Received unhandled event: {event_type}")

    # IMPORTANT: Paystack expects a 200 OK response quickly.
    return {"status": "success", "message": "Webhook received and processed"}











  # must be a positive integer (Paystack expects kobo)


async def initialize_payment(payment: PaymentRequest, 
                             db: db_dependency):
    
    user_model = db.query(User).filter(User.source_id == payment.metadata.user_id).first() #Add lower here for accuracy
    
    if not user_model:
        raise HTTPException(status_code=404, detail="User not found")
    
    payment.metadata.wallet_id = user_model.wallets[0].id
    payment.amount *= 100 #Conversion to Kobo for paystack
    
    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET}",
        "Content-Type": "application/json"
    }

    # Send request to Paystack API
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payment.dict(), headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    data = response.json()
    if not data.get("status"):
        raise HTTPException(status_code=400, detail=data.get("message", "Paystack error"))

    auth_url = data["data"]["authorization_url"]
    reference = data["data"]["reference"]

    # Add transaction to Database
    new_transaction = WalletTransaction(
        wallet_id=user_model.wallets[0].id,  # you can later set this from user's wallet
        transaction_type=TransactionType.DEPOSIT,
        amount=payment.amount/100,
        status=TransactionStatus.PENDING,
        reference_code=reference,
        timestamp=datetime.utcnow()
    )

    db.add(new_transaction)
    db.commit()

    # Redirect user to Paystack checkout
    RedirectResponse(url=auth_url)
    
    return {
        "checkout_url": auth_url,
        "reference": reference,
    }
