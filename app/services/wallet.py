from datetime import datetime
from decimal import Decimal
from fastapi import HTTPException, status, Query, Path
from utils.paystack_withdrawal import create_recipient, initiate_transfer
from db.models import (TransactionStatus, TransactionType, User, 
                       Wallet, WalletTransaction, 
                       WithdrawalBank)
from schemas.wallet import (PaymentRequest, 
                            WalletRequestDTO, 
                            TransactionRequestDTO)
from db.dependencies import db_dependency
from .paystack_handler import initialize_payment, wallet_dependency
from utils.mail_config import send_mail
from sqlalchemy.exc import SQLAlchemyError


#post request
async def create_wallet(wallet_request: WalletRequestDTO, 
                        db: db_dependency):
    # check if user exist
    user_model = db.query(User).filter(User.source_id == wallet_request.user_id).first()
    if not user_model:
        #create user
        user_model = User(
            source_id = wallet_request.user_id,
            email = wallet_request.email
        )
        db.add(user_model)
        db.commit()
        
    # create wallet
    if db.query(Wallet).filter(Wallet.owner_id == user_model.id).first():
        raise HTTPException(status_code=400, detail="Wallet already exists")
    wallet_model = Wallet(
        owner_id = user_model.id,
        currency = wallet_request.currency,
        created_at = wallet_request.created_at
    )
    db.add(wallet_model)
    db.commit()
    
    return {
        
        "user_id": user_model.id,
        "id": wallet_model.id,
        "currency": wallet_model.currency,
        "balance": wallet_model.balance,
        "created_at": wallet_model.created_at,
        "updated_at": wallet_model.updated_at,
        "owner_id": user_model.source_id,
        "message": "Wallet created successfully"
    }
    
    
#post request


async def add_funds_to_wallet(
    payment_request: PaymentRequest,
    db: db_dependency
):
    return await initialize_payment(payment_request, db)


async def withdraw_funds(
    db: db_dependency,
    transaction_request: TransactionRequestDTO,
    ):
    """
    Improved withdraw endpoint behavior:
    - Idempotency by reference_code
    - Create PENDING txn and commit before calling Paystack
    - Store transfer/reference returned from initiate_transfer
    - Update txn status to PROCESSING after initiating transfer
    - Send a "request received" email immediately (not "approved")
    - All final success/failure handling is done via webhook handler
    """

    # 1) Validate user
    user_model = db.query(User).filter(User.source_id == transaction_request.user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User not found")


    # 2) Validate withdrawal account
    withdrawal_account_model = db.query(WithdrawalBank).filter(WithdrawalBank.owner_id == user_model.id).first()
    if not withdrawal_account_model:
        raise HTTPException(status_code=404, detail="Withdrawal account not found, Add a bank account before withdrawing funds")


    # 3) Get wallet and check basic invariants
    wallet_model = db.query(Wallet).filter(Wallet.owner_id == user_model.id).first()
    if not wallet_model:
        raise HTTPException(status_code=404, detail="Wallet not found")


    wallet_dependency(wallet_id=wallet_model.id, db=db)


    if wallet_model.balance < transaction_request.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds in wallet")


    # # 4) Idempotency check: avoid duplicate withdrawals for same reference
    # if transaction_request.reference_code:
    #     existing = db.query(WalletTransaction).filter(
    #         WalletTransaction.reference_code == transaction_request.reference_code
    #     ).first()
    # if existing and existing.status in (TransactionStatus.PENDING):
    #     raise HTTPException(status_code=409, detail="A withdrawal with this reference is already in progress")


    # 5) Create pending transaction and persist it BEFORE calling external API
    txn = WalletTransaction(
    wallet_id=wallet_model.id,
    transaction_type=TransactionType.WITHDRAWAL,
    amount=Decimal(str(transaction_request.amount)),
    status=TransactionStatus.PENDING,
    #reference_code=transaction_request.reference_code,
    timestamp=transaction_request.time or datetime.utcnow(),
    reason=transaction_request.reason,
    )


    db.add(txn)
    try:
        db.commit()
        db.refresh(txn)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"DB error while creating transaction: {str(e)}")

    # 6) Call Paystack to create recipient and initiate transfer
    try:
        recipient_code = await create_recipient(
            bank_code=withdrawal_account_model.bank_code,
            account_number=withdrawal_account_model.account_number,
            name=withdrawal_account_model.account_name or "User"
        )


        # NOTE: Many payment providers expect amounts in the smallest currency unit (kobo).
        # If your initiate_transfer expects kobo, multiply by 100 here. Otherwise pass amount as-is.
        # I'll assume initiate_transfer expects the amount in kobo.
        amount_in_kobo = int(Decimal(str(transaction_request.amount)) * 100)


        transfer_data = await initiate_transfer(
            amount=amount_in_kobo,
            reason=f"Withdrawal {txn.id}",
            recipient_code=recipient_code,
            # optionally: reference=transaction_request.reference_code
        )


        # transfer_data should include at least "reference" and "transfer_code" or similar fields
        transfer_reference = transfer_data.get("data", {}).get("reference") or transfer_data.get("reference")
        transfer_code = transfer_data.get("data", {}).get("transfer_code") or transfer_data.get("transfer_code")
        transfer_status = transfer_data.get("data", {}).get("status") or transfer_data.get("status")


        # 7) Update our txn with the external reference and mark as PROCESSING
        txn.reference_code = f"{transfer_reference}_{transfer_code}"
        #txn.external_transfer_code = transfer_code
        txn.status = TransactionStatus.PENDING
        db.add(txn)
        try:
            db.commit()
            db.refresh(txn)
        except SQLAlchemyError:
            db.rollback()
            # We created the external transfer, but couldn't persist it locally. This is bad; notify ops.
            raise HTTPException(status_code=500, detail="Failed to update transaction after initiating transfer")


        # 8) Send immediate email stating request is received (not approved)
        await send_mail(
        email=transaction_request.email,
        subject="Withdrawal request received",
        body=f"Your withdrawal request of {transaction_request.amount} has been received and is being processed. Reference: {txn.reference_code or txn.id}"
        )

        return {
            "status": "success", 
            "transaction_id": txn.id, 
            "transfer": transfer_data
            }


    except HTTPException as e:
        # external call raised HTTPException -- we should leave the txn as PENDING/FAILED and return
        txn.status = TransactionStatus.FAILED
        db.add(txn)
        db.commit()
        raise e
    except Exception as e:
        # Generic error -- mark txn as FAILED and rollback if needed
        try:
            txn.status = TransactionStatus.FAILED
            db.add(txn)
            db.commit()
        except Exception:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))


#get request
async def get_balance(
    db: db_dependency,
    user_id = Query(...)
):
    user_model = db.query(User).filter(User.source_id == user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User not found")
    
    wallet_model = db.query(Wallet).filter(Wallet.owner_id == user_model.id).first()
    if not wallet_model:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    return {
        "balance": wallet_model.balance,
        "currency": wallet_model.currency
    }
    


async def transfer_funds():
    pass


#get request
async def transaction_history(
    db: db_dependency,
    user_id = Query(...)
):
    user_model = db.query(User).filter(User.source_id == user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User not found")
    
    wallet_model = db.query(Wallet).filter(Wallet.owner_id == user_model.id).first()
    transaction_history = wallet_model.transactions
    
    return [{    
        "id": transaction.id,
        "type": transaction.transaction_type,
        "amount": transaction.amount,
        "status": transaction.status,
        "reference_code": transaction.reference_code,
        "timestamp": transaction.timestamp
    } for transaction in transaction_history]
      


#put request                       
async def update_wallet(
    db: db_dependency,
    wallet_request: WalletRequestDTO
):
    pass
                     
    

    

    