from fastapi import HTTPException, status, Query, Path
from utils.paystack_withdrawal import create_recipient, initiate_transfer
from db.models import (TransactionStatus, TransactionType, User, 
                       Wallet, WalletTransaction, 
                       WithdrawalBank)
from schemas.wallet import (PaymentRequest, 
                            WalletRequestDTO, 
                            TransactionRequestDTO)
from db.dependencies import db_dependency
#from .paystack_handler import initialize_payment
from utils.mail_config import send_mail
from utils.mail_config import send_mail


async def get_all_wallets(
    db: db_dependency = db_dependency
):
    wallets = db.query(Wallet).all()
    return wallets


async def get_wallet_by_user_id(
    db: db_dependency,
    user_id: str = Query(..., description="The ID of the user whose wallet to retrieve")
):
    wallet = db.query(Wallet).join(User).filter(User.source_id == user_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found for the specified user")
    return wallet

#post request
async def credit_wallet(
    transaction_request: TransactionRequestDTO,
    db: db_dependency
):
    wallet = db.query(Wallet).join(User).filter(User.source_id == transaction_request.user_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found for the specified user")
    
    new_transaction = WalletTransaction(
        wallet_id=wallet.id,
        transaction_type=TransactionType.CREDIT,
        amount=transaction_request.amount,
        status=TransactionStatus.SUCCESS,
        reference_code=transaction_request.reference_code,
        timestamp=transaction_request.time,
        reason=transaction_request.reason
    )
    db.add(new_transaction)
    
    wallet.balance += transaction_request.amount
    db.commit()
    db.refresh(new_transaction)
    
    send_mail(
        email=wallet.owner.email,
        subject="Wallet Credited",
        body= f'''
        Your wallet has been credited with {transaction_request.amount} {wallet.currency}.
        New Balance: {wallet.balance} {wallet.currency}
        '''
    )
    
    return {
        "message": "Wallet credited successfully"
    }
    
    
#post request
async def debit_wallet(
    transaction_request: TransactionRequestDTO,
    db: db_dependency
):
    wallet = db.query(Wallet).join(User).filter(User.source_id == transaction_request.user_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found for the specified user")
    
    if wallet.balance < transaction_request.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds in wallet")
    
    new_transaction = WalletTransaction(
        wallet_id=wallet.id,
        transaction_type=TransactionType.WITHDRAWAL,
        amount=transaction_request.amount,
        status=TransactionStatus.SUCCESS,
        reference_code=transaction_request.reference_code,
        timestamp=transaction_request.time,
        reason=transaction_request.reason
    )
    db.add(new_transaction)
    
    wallet.balance -= transaction_request.amount
    db.commit()
    db.refresh(new_transaction)
    
    send_mail(
        email=wallet.owner.email,
        subject="Wallet Debited",
        body= f'''
        Your wallet has been debited by {transaction_request.amount} {wallet.currency}.
        New Balance: {wallet.balance} {wallet.currency}
        '''
    )
    
    return {
        "message": "Wallet debited successfully"
    }
    
    
async def get_wallet_transactions(
    db: db_dependency,
    user_id: str = Query(..., description="The ID of the user whose wallet transactions to retrieve")
):
    wallet = db.query(Wallet).join(User).filter(User.source_id == user_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found for the specified user")
    
    transactions = db.query(WalletTransaction).filter(WalletTransaction.wallet_id == wallet.id).all()
    
    return transactions


#put request
async def update_wallet(
    db: db_dependency,
    wallet_request: WalletRequestDTO
):
    pass


#post request
async def freeze_wallet(
    db: db_dependency = db_dependency,
    user_id: str = Query(..., description="The ID of the user whose wallet to freeze")
):
    
    user_model = db.query(User).filter(User.source_id == user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User not found")
    
    wallet = db.query(Wallet).join(User).filter(User.source_id == user_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found for the specified user")
    
    wallet.is_frozen = True
    db.commit()
    
    send_mail(
        email=user_model.email,
        subject="Wallet Frozen",
        body= f'''
        Your wallet has been frozen due to suspicious activities. Please contact support for more information.
        '''
    )
    
    return {
        "message": "Wallet frozen successfully"
    }
    
    
async def unfreeze_wallet(
    db: db_dependency,
    user_id: str = Query(..., description="The ID of the user whose wallet to unfreeze")
):
    user_model = db.query(User).filter(User.source_id == user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User not found")
    
    wallet = db.query(Wallet).join(User).filter(User.source_id == user_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found for the specified user")
    
    wallet.is_frozen = False
    db.commit()
    
    send_mail(
        email=user_model.email,
        subject="Wallet Unfrozen",
        body= f'''
        Your wallet has been unfrozen.
        Please contact support for more information.
        '''
    )
    
    return {
        "message": "Wallet unfrozen successfully"
    }