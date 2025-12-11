from decimal import Decimal
from db.dependencies import db_dependency
from fastapi import HTTPException, Depends, Path, Query
from schemas.escrow import (TransactionInstance, TransactionMilestoneInstance, UserConfirmMilestone, UserConfirmation, 
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
            merchant_model = db.query(User).filter(User.source_id == transaction_instance.merchant_id).first()
            if not user_model:
                raise HTTPException(status_code=404, detail="User not found")
            if not merchant_model:
                raise HTTPException(status_code=404, detail="User not found")
            
            project_model = db.query(Escrow).filter(
                Escrow.project_id==transaction_instance.project_id,
                Escrow.merchant_id==merchant_model.id
            ).first()
            if project_model:
                raise HTTPException(status_code=404, detail="Escrow project exist")
            if project_model.client_id != user_model.id:
                raise HTTPException(status_code=403, detail=f"Wrong client id {project_model.client_id}  {transaction_instance.client_id}")

                  
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
    
    
    
async def create_milestone_transaction(
    transaction_instance: TransactionMilestoneInstance,
    db: db_dependency,
):
    """
    Docstring for create_milestone_transaction"""
    merchant_id = db.query(User).filter(User.source_id == transaction_instance.merchant_id).first()
    project_models = db.query(Escrow).filter(Escrow.project_id == transaction_instance.project_id).all()
    for project_model in project_models:
        if project_model.merchant_id == transaction_instance.merchant_id:
            project_model=project_model
            break
        project_model = None
    project_model = db.query(Escrow).filter(
        Escrow.project_id == transaction_instance.project_id,
        Escrow.merchant_id == transaction_instance.merchant_id
        ).first()
    if not project_model:
        client_model = db.query(User).filter(User.source_id == transaction_instance.client_id).first()
        if not client_model:
            raise HTTPException(status_code=404, detail="Client not found")
        merchant_model = db.query(User).filter(User.source_id == transaction_instance.merchant_id).first()
        if not merchant_model:
            raise HTTPException(status_code=404, detail="Merchant not found")
        
        # create project
        project_model = Escrow(
            project_id=transaction_instance.project_id,
            client_id = client_model.id,
            amount = 0.00,
            merchant_id=merchant_model.id,
            status=EscrowStatus.PENDING,
            created_at=datetime.now()
        )
        db.add(project_model)
        db.flush()
    amount = Decimal(0.00)       
    #create milestone
    for milestone in transaction_instance.milestone:
        milestone_model = Milestones(
            key=milestone.key,
            escrow_id= transaction_instance.project_id,
            milestone_name=milestone.title,
            description=milestone.description,
            amount=milestone.amount,
            finished=False
        )
        amount += milestone.amount
        db.add(milestone_model)
        
    wallet_model = db.query(Wallet).filter(Wallet.owner_id == project_model.client_id).first()
    wallet_model.balance -= amount
    project_model.status = EscrowStatus.FUNDED
    
    db.commit()
    
    return {
        "project_id": transaction_instance.project_id,
    }
    
    
async def client_confirm_milestone(
    user_confirmation: UserConfirmMilestone,
    db: db_dependency,
):
    user_model = db.query(User).filter(User.source_id == user_confirmation.client_id).first()
    merchant_model = db.query(User).filter(User.source_id ==user_confirmation.merchant_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User does not exist")
        
    escrow_model = db.query(Escrow).filter(
        Escrow.project_id == user_confirmation.project_id,
        Escrow.merchant_id == merchant_model.id
    ).first()
    
    if not escrow_model:
        raise HTTPException(status_code=404, detail=f"Escrow not found {merchant_model.id}, {escrow_model.merchant_id}")
    
    merchant_model = db.query(User).filter(User.id == escrow_model.merchant_id).first()
    
    if not merchant_model:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    check_transaction_cancelability(escrow_model.id, db)
    check_transaction_disputability(db, escrow_model.id)
    
    milestone_models = db.query(Milestones).filter(Milestones.key == user_confirmation.milestone_key).all()
    if not milestone_models:
        raise HTTPException(status_code=404, detail="Milestone not found")
    if escrow_model.project_id not in [m.escrow_id for m in milestone_models]:
        raise HTTPException(status_code=404, detail=f"Milestone not assigned to this project {escrow_model.project_id}, {milestone_model.escrow_id}")
    
    for m in milestone_models:
        milestone_model = m if m.key == user_confirmation.milestone_key else None
    
    if milestone_model.finished:
        raise HTTPException(status_code=400, detail="Milestone already finished")

    if escrow_model.client_id != user_model.id:
        raise HTTPException(status_code=401, detail="Client not authorized to confirm this transaction")
    if escrow_model.merchant_id != merchant_model.id:
        raise HTTPException(status_code=401, detail="Merchant not authorized to this transaction")
    
    wallet_model = db.query(Wallet).filter(Wallet.owner_id == escrow_model.merchant_id).first()
    wallet_model.balance += milestone_model.amount
    milestone_model.finished = True
    escrow_model.status = EscrowStatus.RELEASED
   
    db.commit()
    return {
        "project_id":user_confirmation.project_id,
        "milestone_key":user_confirmation.milestone_key,
        "status": escrow_model.status,
        "message": "Transaction confirmed successfully"
    }
    
    
async def get_transaction_history(
    db: db_dependency,
    user_id = Query(...),
    actor = Query(...)
):
    if actor not in ["merchant", "client"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid actor type, 'client' or 'merchant' expected"
        )
    
    # Fetch user
    user_model = db.query(User).filter(User.source_id == user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Fetch transactions based on role
    if actor == "merchant":
        transactions = (
            db.query(Escrow)
            .filter(Escrow.merchant_id == user_model.id)
            .all()
        )
    else:  # actor == "client"
        transactions = (
            db.query(Escrow)
            .filter(Escrow.client_id == user_model.id)
            .all()
        )

    # Build response per transaction
    results = []
    
    for transaction in transactions:
        
        # Filter finished milestones for this specific transaction
        finished_milestones = [
            {
                "id": m.id,
                "key": m.key,
                "name": m.milestone_name,
                "amount": float(m.amount),
                "description": m.description,
                "finished": m.finished
            }
            for m in transaction.milestones
        ]

        results.append({
            "project_id": transaction.project_id,
            "status": transaction.status.value,
            "amount": float(transaction.amount),
            "created_at": transaction.created_at,
            "finalized_at": transaction.finalized_at,
            "milestones": finished_milestones or None
        })
    
    return results


async def get_transaction_by_id(
    db: db_dependency,
    project_id: str = Query(...),
    merchant_id: str = Query(...)
):
    """
    Fetch escrow transaction by project_id and return
    all finished milestones.
    """
    merchant_model = db.query(User).filter(User.source_id == merchant_id).first()
    if not merchant_model:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    transaction_model = db.query(Escrow).filter(
            Escrow.project_id == project_id,
            Escrow.merchant_id == merchant_model.id).first()
    
    if not transaction_model:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # 2. Filter milestones where finished == True
    finished_milestones = [
        {
            "id": m.id,
            "key": m.key,
            "name": m.milestone_name,
            "amount": float(m.amount),  # Or use str(m.amount)
            "description": m.description,
            "finished": m.finished
        }
        for m in transaction_model.milestones
        if m.finished is True
    ]

    # 3. Return the escrow + the milestone data
    return {
        "project_id": transaction_model.project_id,
        "status": transaction_model.status,
        "amount": float(transaction_model.amount),  # JSON can't serialize Decimal
        "created_at": transaction_model.created_at,
        "finalized_at": transaction_model.finalized_at,
        "milestones": finished_milestones or None

    }


async def client_confirm_transaction(
    user_confirmation: UserConfirmation,
    db: db_dependency,
    #actor: str = Path(..., description="Either 'client' or 'merchant'")
):

    user_model = db.query(User).filter(User.source_id == user_confirmation.client_id).first()
    merchant_model = db.query(User).filter(User.source_id ==user_confirmation.merchant_id).first()

    if not user_model:
        raise HTTPException(status_code=404, detail="User does not exist")
    
    escrow_model = db.query(Escrow).filter(
        Escrow.project_id == user_confirmation.project_id,
        Escrow.merchant_id == merchant_model.id
    ).first()
    if not escrow_model:
        raise HTTPException(status_code=404, detail="Escrow not found")
    
    if not (escrow_model.client_id == user_model.id):
        raise HTTPException(status_code=401, detail="Client not authorized to confirm this transaction")
       
    check_transaction_cancelability(escrow_model.id, db)
    
    if escrow_model.status != EscrowStatus.FUNDED:
        raise HTTPException(status_code=400, detail="Transaction not funded or has been released")
    
    
    
    check_transaction_disputability(db, escrow_model.id)
    merchant_wallet = db.query(Wallet).filter(Wallet.owner_id == escrow_model.merchant_id).first()
    
    escrow_model.client_agree = user_confirmation.confirm_status
    
    if escrow_model.client_agree:
        merchant_wallet.balance += escrow_model.amount
        escrow_model.status = EscrowStatus.RELEASED
        escrow_model.finalized_at = datetime.now()
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
    user_model = db.query(User).filter(User.source_id == release_funds.client_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User does not exist")
    merchant_model = db.query(User).filter(User.source_id == release_funds.merchant_id).first()
    if not merchant_model: 
        raise HTTPException(status_code=404, detail="User does not exist")
    escrow_model = db.query(Escrow).filter(
    # Filter by project_id
    Escrow.project_id == release_funds.project_id,
    # AND filter by merchant_id
    Escrow.merchant_id == merchant_model.id
).first()
    
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
    

async def update_transactions():
    pass


async def cancel_transaction(
    db: db_dependency,
    cancel_request: CancelRequest
):
    user_model = db.query(User).filter(User.source_id == cancel_request.client_id).first()
    merchant_model = db.query(User).filter(User.source_id ==cancel_request.merchant_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User does not exist")
        
    escrow_model = db.query(Escrow).filter(
        Escrow.project_id == cancel_request.project_id,
        Escrow.merchant_id == merchant_model.id
    ).first()
    if not escrow_model:
        raise HTTPException(status_code=404, detail="Escrow not found")
        
        
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
    
    
    user_model = db.query(User).filter(User.source_id == dispute_request.client_id).first()
    merchant_model = db.query(User).filter(User.source_id ==dispute_request.merchant_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User does not exist")
    
    escrow_model = db.query(Escrow).filter(
        Escrow.project_id == dispute_request.project_id,
        Escrow.merchant_id == merchant_model.id
    ).first()
    if not escrow_model:
        raise HTTPException(status_code=404, detail="Escrow not found")
    
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
                            id: str, 
                            ):
    escrow_model = db.query(Escrow).filter(Escrow.id == id).first()
    
    if not escrow_model:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if escrow_model.status == EscrowStatus.DISPUTED:
        raise HTTPException (status_code=403, detail="Transaction disputed.")
    
    pass
    