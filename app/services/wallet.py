from fastapi import HTTPException, status, Query, Path
from utils.paystack_withdrawal import create_recipient, initiate_transfer
from db.models import (User, 
                       Wallet, 
                       WithdrawalBank)
from schemas.wallet import (PaymentRequest, 
                            WalletRequestDTO, 
                            TransactionRequestDTO)
from db.dependencies import db_dependency
from .paystack_handler import initialize_payment
from utils.mail_config import send_mail



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
    withdrawal_account_id = Query(...),      
):
    
    user_model = db.query(User).filter(User.source_id == transaction_request.user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User not found")
    
    withdrawal_account_model = db.query(WithdrawalBank).filter(WithdrawalBank.id == withdrawal_account_id).first()
    if not withdrawal_account_model:
        raise HTTPException(status_code=404, detail="Withdrawal account not found")
    
    if withdrawal_account_model.owner_id != user_model.id:
        raise HTTPException(status_code=401, detail="You are not authorized to withdraw to this account")
    
    print("Reached here")
    
    try:
        # Step 1: Create transfer recipient
        recipient_code = await create_recipient(
            bank_code=withdrawal_account_model.bank_code,
            account_number=withdrawal_account_model.account_number,
            name=withdrawal_account_model.account_name or "User"
        )

        # Step 2: Initiate transfer
        transfer_data = await initiate_transfer(
            amount=transaction_request.amount,
            reason="Withdrawal to local account",
            recipient_code=recipient_code
        )
        
        await send_mail(
            email= transaction_request.email,
            subject= "Withdrawal Approved",
            body= f"""
            You just withdrew, {transaction_request.amount} to your local account.
            Bank Name: {withdrawal_account_model.bank_name}
            Account Name: {withdrawal_account_model.account_name}
            Account Number: {withdrawal_account_model.account_number}
            """
        )
        return {"status": "success", "transfer": transfer_data}

    except HTTPException as e:
        raise e
    except Exception as e:
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
                     
    
    