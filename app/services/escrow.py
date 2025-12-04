from decimal import Decimal
from db.dependencies import db_dependency
from fastapi import HTTPException, Depends, Path, Query
from schemas.escrow import (TransactionInstance, UserConfirmation, 
                            ReleaseFunds, CancelRequest,
                            DisputeRequest, Milestone)
from db.models import (Escrow, 
                       EscrowStatus, 
                       User, 
                       Wallet, 
                       WalletTransaction, 
                       TransactionType, 
                       TransactionStatus,
                       EscrowTransaction,
                       Milestones)
from db.dependencies import db_dependency
from datetime import datetime
from sqlalchemy import or_



async def create_transaction(
    transaction_instance: TransactionInstance,
    db: db_dependency,
):
    """
    Docstring for create_transaction
    
    :param transaction_instance: Description
    :type transaction_instance: The transaction instance schema
        merchant_id
        client_id
        project_id 
        amount should be greater than 0.00
    """
    try:
        with db.begin():  # atomic transaction
            user_model = db.query(User).filter(User.source_id == transaction_instance.client_id).first()
            if not user_model:
                raise HTTPException(status_code=404, detail="User not found")
            
            project_model = db.query(Escrow).filter(Escrow.project_id==transaction_instance.project_id).first()
            if project_model:
                raise HTTPException(status_code=403, detail="Project already exist.")

            merchant_model = db.query(User).filter(User.source_id == transaction_instance.merchant_id).first()
            if not merchant_model:
                raise HTTPException(status_code=404, detail="Merchant not found")

            escrow_model = Escrow(
                client_id=user_model.id,
                merchant_id=merchant_model.id,
                amount=transaction_instance.amount,
                status=EscrowStatus.PENDING, #change to funded.
                created_at=datetime.now(),
                project_id = transaction_instance.project_id
            )
            db.add(escrow_model)

        return {
            "project_id": escrow_model.project_id,
            "status": escrow_model.status,
            "amount": escrow_model.amount,
            "message": "Transaction created successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")
    
    
async def create_milestone_transaction(
    transaction_instance: TransactionInstance,
    db: db_dependency,
):
    user_model = db.query(User).filter(User.source_id == transaction_instance.client_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User not found")
       
    merchant_model = db.query(User).filter(User.source_id == transaction_instance.merchant_id).first()
    if not merchant_model:
        raise HTTPException(status_code=404, detail="Merchant not found")    
    user_wallet_model = db.query(Wallet).filter(Wallet.owner_id == user_model.id).first()    
    if not user_wallet_model:
        raise HTTPException(status_code=404, detail="User wallet not found")
    
    total_milestone_amount = sum(m.amount for m in transaction_instance.milestone)

    if transaction_instance.amount != total_milestone_amount:
        raise HTTPException(status_code=400, detail=f"Invalid amount {total_milestone_amount},{transaction_instance.amount}")

    
    if user_wallet_model.balance < transaction_instance.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    user_wallet_model.balance -= transaction_instance.amount
    
    escrow_model = Escrow(
                client_id=user_model.id,
                merchant_id=merchant_model.id,
                amount=transaction_instance.amount,
                status=EscrowStatus.FUNDED, #change to funded.
                created_at=datetime.now(),
                project_id = transaction_instance.project_id
            )
    db.add(escrow_model)
    db.flush()

    for milestone in transaction_instance.milestone:
        milestone_model = Milestones(
            key=milestone.key,
            escrow_id= escrow_model.id,
            milestone_name=milestone.milestone_name,
            description=milestone.description,
            amount=milestone.amount
        )
        db.add(milestone_model)
        
    db.add(escrow_model)
    db.commit()
    return {
            "project_id": escrow_model.project_id,
            "status": escrow_model.status,
            "amount": escrow_model.amount,
            "message": "Transaction created successfully"
        }
    
    
async def client_confirm_milestone(
    user_confirmation: UserConfirmation,
    db: db_dependency,
):
    user_model = db.query(User).filter(User.source_id == user_confirmation.user_id).first()

    if not user_model:
        raise HTTPException(status_code=404, detail="User does not exist")
    escrow_model = db.query(Escrow).filter(Escrow.project_id == user_confirmation.project_id).first()
    if not escrow_model:
        raise HTTPException(status_code=404, detail="Escrow not found")
    
    merchant_model = db.query(User).filter(User.id == escrow_model.merchant_id).first()
    
    if not merchant_model:
        raise HTTPException(status_code=404, detail="Merchant not found")

    milestone_model = (
    db.query(Milestones)
    .filter(
        Milestones.escrow_id == escrow_model.id,
        Milestones.key == user_confirmation.milestone_key
    )
    .first()
)
    if not milestone_model:
        raise HTTPException(status_code=404, detail=f"Milestone not found {milestone_model}")

    if escrow_model.client_id != user_model.id:
        raise HTTPException(status_code=401, detail="Client not authorized to confirm this transaction")
    if escrow_model.merchant_id != merchant_model.id:
        raise HTTPException(status_code=401, detail="Merchant not authorized to this transaction")
    
    wallet_model = db.query(Wallet).filter(Wallet.owner_id == escrow_model.merchant_id).first()
    wallet_model.balance += milestone_model.amount
    milestone_model.finished = True
   
    db.commit()
    return {
        "project_id":user_confirmation.project_id,
        "milestone_key":user_confirmation.milestone_key,
        "status": escrow_model.status,
        "message": "Transaction confirmed successfully"
    }
    
    
#get request
async def get_transaction_history(
    db: db_dependency,
    user_id = Query(...),
    actor = Query(...)
):
    if actor not in ["merchant", "client"]:
        raise HTTPException(status_code=400, detail="Invalid actor type, 'client' or 'merchant' expected")
    
    user_model = db.query(User).filter(User.source_id == user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User not found")
    
    if actor == "merchant":
        transaction_model = db.query(Escrow).filter(Escrow.merchant_id == user_model.id).all()
        
    elif actor == "client":
        transaction_model = db.query(Escrow).filter(Escrow.client_id == user_model.id).all()
    
    return [
        {
        "project_id": transaction.project_id,
        "status": transaction.status,
        "amount": transaction.amount,
        "created_at": transaction.created_at,
        "finalized_at": transaction.finalized_at
    } 
        for transaction in transaction_model]


async def get_transaction_by_id(
    db: db_dependency,
    project_id = Query(...)
):
    """
    Docstring for get_transaction_by_id
    
    :param project_id: This is the project ID associated with the 
        transaction on wordpress
    :type project_id: str
    """
    transaction_model = db.query(Escrow).filter(Escrow.project_id == project_id).first()
    if not transaction_model:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return {
        "project_id": transaction_model.project_id,
        "status": transaction_model.status,
        "amount": transaction_model.amount,
        "created_at": transaction_model.created_at,
        "finalized_at": transaction_model.finalized_at
    }



    
    

async def client_confirm_transaction(
    user_confirmation: UserConfirmation,
    db: db_dependency,
    #actor: str = Path(..., description="Either 'client' or 'merchant'")
):

    
    user_model = db.query(User).filter(User.source_id == user_confirmation.user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User does not exist")
    
    escrow_model = db.query(Escrow).filter(Escrow.project_id == user_confirmation.project_id).first()
    check_transaction_cancelability(escrow_model.id, db)
    if not escrow_model:
        raise HTTPException(status_code=404, detail="Escrow not found")
    check_transaction_disputability(db, escrow_model.id)
    
    if not escrow_model.client_id == user_model.id:
        raise HTTPException(status_code=401, detail="Client not authorized to confirm this transaction")
    
    check_transaction_disputability(db, escrow_model.id)
    
    escrow_model.client_agree = user_confirmation.confirm_status
    db.commit()
    
    return {
        "project_id": escrow_model.project_id,
        "status": escrow_model.status,
        "message": "Transaction confirmed successfully"
    }
    
    
async def merchant_confirm_transaction(
    user_confirmation: UserConfirmation,
    db: db_dependency,
    #actor: str = Path(..., description="Either 'client' or 'merchant'")
):
    user_model = db.query(User).filter(User.source_id == user_confirmation.user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User does not exist")
    
    escrow_model = db.query(Escrow).filter(Escrow.project_id == user_confirmation.project_id).first()
    if not escrow_model:
        raise HTTPException(status_code=404, detail="Escrow not found")
    
    check_transaction_cancelability(escrow_model.id, db)
    check_transaction_disputability(db, escrow_model.id)

    
    if not escrow_model.merchant_id == user_model.id:
        raise HTTPException(status_code=401, detail="Client not authorized to confirm this transaction")
    
    escrow_model.merchant_agree = user_confirmation.confirm_status
    db.commit()
    
    return {
        "project_id": escrow_model.project_id,
        "status": escrow_model.status,
        "message": "Transaction confirmed successfully"
    }
    

async def client_release_funds(
    db: db_dependency,
    release_funds: ReleaseFunds
):
    user_model = db.query(User).filter(User.source_id == release_funds.user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User does not exist")

    escrow_model = db.query(Escrow).filter(Escrow.project_id == release_funds.project_id).first()
    if not escrow_model:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if user_model.id != escrow_model.client_id:
        raise HTTPException(status_code=401, detail="Client not authorized")
    
    check_transaction_cancelability(escrow_model.id, db)
    check_transaction_disputability(db, escrow_model.id)
    
    wallet_model = (
                db.query(Wallet)
                .filter(Wallet.owner_id == user_model.id)
                .with_for_update()
                .first()
            )
    if not wallet_model:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    if escrow_model.status != EscrowStatus.PENDING:
        return {
            "id": escrow_model.id,
            "status": escrow_model.status,
            "message": "Transaction is not pending, you can't release funds"
        }

    amount = Decimal(escrow_model.amount)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid transaction amount")
    if wallet_model.balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    wallet_model.balance -= amount
    escrow_model.status = EscrowStatus.FUNDED
    db.commit()
    return {
        "project_id": escrow_model.project_id,
        "status": escrow_model.status,
        "message": "Funds released successfully"
    }
    
    
async def merchant_release_funds(
    db: db_dependency,
    release_funds: ReleaseFunds
):
    
    user_model = db.query(User).filter(User.source_id == release_funds.user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User does not exist")

    escrow_model = db.query(Escrow).filter(Escrow.project_id == release_funds.project_id).first()
    
    if not escrow_model:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if user_model.id != escrow_model.merchant_id:
        raise HTTPException(status_code=401, detail="Merchant not authorized")
    
    check_transaction_cancelability(escrow_model.id, db)
    check_transaction_disputability(db, escrow_model.id)
    
    
    if not (escrow_model.merchant_agree and escrow_model.client_agree):
        raise HTTPException(status_code=400, detail="Transaction not confirmed by both parties")
    
    if escrow_model.status != EscrowStatus.FUNDED:
        raise HTTPException(status_code=400, detail="Transaction is not pending")
    
    wallet_model = db.query(Wallet).filter(Wallet.owner_id == user_model.id).first()

    wallet_model.balance += escrow_model.amount
    escrow_model.finalized_at = datetime.now()
    #add to wallet transaction
    txn = WalletTransaction(
        wallet_id=wallet_model.id,
        amount=escrow_model.amount,
        transaction_type=TransactionType.ESCROW_RELEASE,
        status=TransactionStatus.SUCCESS,
        timestamp=datetime.now()
    )
    db.add(txn)
    
    escrow_model.status = EscrowStatus.RELEASED
    db.commit()
    return {
        "project_id": escrow_model.project_id,
        "status": escrow_model.status,
        "message": "Funds released successfully"
    }

    




async def update_transactions():
    pass


async def cancel_transaction(
    db: db_dependency,
    cancel_request: CancelRequest
):
    user_model = db.query(User).filter(User.source_id == cancel_request.user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User does not exist")
    

    escrow_model = db.query(Escrow).filter(Escrow.project_id == cancel_request.project_id).first()
    
    if escrow_model.client_id != user_model.source_id:
        if escrow_model.merchant_id != user_model.source_id:
            raise HTTPException(status_code=401, detail="You are not authorized to cancel this transaction")
        pass
    
    escrow_model.status = EscrowStatus.CANCELLED
    escrow_model.finalized_at = datetime.now()
    db.commit()
    
    return {
        "project_id": escrow_model.project_id,
        "status": escrow_model.status,
        "message": "Transaction cancelled successfully"
    }
    
    
    
    
def check_transaction_cancelability(id: str, 
                             db: db_dependency):
    escrow_model = db.query(Escrow).filter(Escrow.id == id).first()
    
    if not escrow_model:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if escrow_model.status == EscrowStatus.CANCELLED:
        raise HTTPException (status_code=403, detail="Transaction cancelled.")
    
    
async def dispute_transaction(
                            db: db_dependency,
                            dispute_request: DisputeRequest
                            ):
    """
    Docstring for dispute_transaction
    
    :param dispute_request: For disputing an escrow transaction
    :type dispute_request: {escrow_id: str
                            user_id: str 
                            reason: // is optional}
    """
    
    
    user_model = db.query(User).filter(User.source_id == dispute_request.user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User does not exist")
    
    escrow_model = db.query(Escrow).filter(Escrow.project_id == dispute_request.project_id).first()
    if not escrow_model:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if escrow_model.client_id != user_model.source_id:
        if escrow_model.merchant_id != user_model.source_id:
            raise HTTPException(status_code=401, detail="You are not authorized to dispute this transaction")
        pass
    
    escrow_model.status = EscrowStatus.DISPUTED
    
    if escrow_model.status != EscrowStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending transactions can be disputed")
    
    dispute_model = EscrowTransaction(
        escrow_id=dispute_request.project_id,
        amount=escrow_model.amount,
        reason=dispute_request.reason,
        status=EscrowStatus.DISPUTED,
        timestamp=datetime.now()
    )
    db.add(dispute_model)
    db.commit()
    
    return {
        "escrow_id": dispute_request.project_id,
        "reason": dispute_model.reason,
    }
    
    
def check_transaction_disputability(
                            db: db_dependency,
                            escrow_id: str, 
                            ):
    escrow_model = db.query(Escrow).filter(Escrow.id == escrow_id).first()
    
    if not escrow_model:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if escrow_model.status == EscrowStatus.DISPUTED:
        raise HTTPException (status_code=403, detail="Transaction disputed.")
    
    pass
    