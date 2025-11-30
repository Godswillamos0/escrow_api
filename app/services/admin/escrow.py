from decimal import Decimal
from db.dependencies import db_dependency
from fastapi import (HTTPException, 
                     Depends, 
                     Path, 
                     Query)
from schemas.escrow import (TransactionInstance, UserConfirmation, 
                            ReleaseFunds, CancelRequest,
                            DisputeRequest)
from db.models import (Escrow, 
                       EscrowStatus, 
                       User, 
                       Wallet, 
                       WalletTransaction, 
                       TransactionType, 
                       TransactionStatus)
from db.dependencies import db_dependency
from datetime import datetime
from sqlalchemy import asc, or_



async def get_escrow_by_id(project_id: str = Query(..., description="The ID of the escrow transaction to retrieve"),
                      db=Depends(db_dependency)) -> dict:
    escrow = db.query(Escrow).filter(Escrow.project_id == project_id).first()
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow transaction not found")
    return {
        "id": escrow.id,
        "status": escrow.status,
        "amount": escrow.amount,
        "created_at": escrow.created_at,
        "finalized_at": escrow.finalized_at,
        "client_id": escrow.client_id,
        "merchant_id": escrow.merchant_id,
        "client_agree": escrow.client_agree,
        "merchant_agree": escrow.merchant_agree,
    }


async def get_all_transactions(db:db_dependency):
    escrows = db.query(Escrow).all()
    return escrows


async def cancel_transaction(request: CancelRequest, db=Depends(db_dependency)):
    escrow = db.query(Escrow).filter(Escrow.project_id == request.project_id).first()
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow transaction not found")
    
    if escrow.status != EscrowStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending transactions can be cancelled")
    
    escrow.status = EscrowStatus.CANCELLED
    escrow.updated_at = datetime.utcnow()
    db.commit()
    return {
        "detail": "Transaction cancelled successfully"
        }


async def dispute_transaction(project_id: str, reason: str, db:db_dependency):
    escrow = db.query(Escrow).filter(Escrow.project_id == project_id).first()
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow transaction not found")
    
    if escrow.status != EscrowStatus.HELD:
        raise HTTPException(status_code=400, detail="Only held transactions can be disputed")
    
    escrow.status = EscrowStatus.DISPUTED
    escrow.dispute_reason = reason
    escrow.updated_at = datetime.utcnow()
    db.commit()
    return {
        "detail": "Transaction disputed successfully"
        }
    
    
async def get_all_disputed_transactions(db: db_dependency):
    escrows = db.query(Escrow).filter(Escrow.status == EscrowStatus.DISPUTED).all()
    return escrows


async def force_release_funds(request: ReleaseFunds, 
                              db: db_dependency):
    escrow = db.query(Escrow).filter(Escrow.project_id == request.project_id).first()
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow transaction not found")
    
    if escrow.status != EscrowStatus.FUNDED:
        raise HTTPException(status_code=400, detail="Only held transactions can be released")
    
    merchant_model = db.query(User).filter(User.source_id == escrow.merchant_id).first()
    if not merchant_model:
        raise HTTPException(status_code=404, detail="Merchant not found")
    merchant_wallet = db.query(Wallet).filter(Wallet.owner_id == merchant_model.id).first()
    merchant_wallet.balance += escrow.amount
    escrow.status = EscrowStatus.RELEASED
    escrow.updated_at = datetime.utcnow()
    db.commit()
    return {
        "detail": "Funds released successfully"
        }
    
    
async def force_return_funds(request: ReleaseFunds, 
                              db: db_dependency):
    user_model = db.query(User).filter(User.source_id == request.user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User not found")
    

    escrow = db.query(Escrow).filter(Escrow.project_id == request.project_id).first()
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow transaction not found")
    if escrow.status != EscrowStatus.FUNDED:
        raise HTTPException(status_code=400, detail="Only held transactions can be returned")
    
    wallet_model = db.query(Wallet).filter(Wallet.owner_id == escrow.client_id).first()
    if not wallet_model:
        raise HTTPException(status_code=404, detail="Client wallet not found")
    wallet_model.balance += escrow.amount
    escrow.status = EscrowStatus.REFUNDED
    db.add(wallet_model)
    
    escrow.updated_at = datetime.utcnow()
    db.commit()
    return {
        "detail": "Funds returned successfully"
        }


async def resolve_dispute(
    project_id: str, 
    db: db_dependency
    ):
    escrow = db.query(Escrow).filter(Escrow.project_id == project_id).first()
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow transaction not found")
    
    if escrow.status != EscrowStatus.DISPUTED:
        raise HTTPException(status_code=400, detail="Only disputed transactions can be resolved")
    
    escrow.status = EscrowStatus.RELEASED
    escrow.updated_at = datetime.utcnow()
    db.commit()
    return {
        "detail": "Dispute resolved and funds released successfully"
        }
