from fastapi import HTTPException, status, Path
from db.dependencies import db_dependency
from db.models import EscrowStatus, Task, User, Wallet
from datetime import datetime
from decimal import Decimal
from schemas.task import (CompleteTask, CreateTask, UpdateTask)


async def save_task(
    db: db_dependency,
    task: CreateTask
):
    
    client_id = db.query(User).filter(User.source_id == task.client_id).first()
    merchant_id = db.query(User).filter(User.source_id == task.merchant_id).first()
    if not (client_id and merchant_id):
        raise HTTPException(404, "User not found.")
    
    task_model = Task(
        task_id = task.task_id,
        merchant = merchant_id.id,
        client = client_id.id,
        title = task.title,
        amount = task.amount,
        status = EscrowStatus.PENDING
    )
    
    db.add(task_model)
    
    #withdraw from client_id  
    wallet_model = db.query(Wallet).filter(Wallet.owner_id==client_id.id).first()
    
    wallet_model.balance -= task_model.amount
    task_model.status = EscrowStatus.FUNDED
    
    db.commit()
    
    return {
        "detail": "Task created successfully"
    }
    
async def complete_task(
    db: db_dependency,
    task: CompleteTask
):
    merchant_id = db.query(User).filter(User.source_id == task.merchant_id).first()
    client_id = db.query(User).filter(User.source_id == task.client_id).first()
    if not (client_id):
            raise HTTPException(404, "Client not found.")
    if not (merchant_id):
        raise HTTPException(404, "Merchant not found.")
        
    task_model = db.query(Task).filter(
        Task.task_id == task.task_id,
        Task.client == client_id.id,
        Task.merchant == merchant_id.id
    ).first()
    if not task_model:
        raise HTTPException(404, "Task not found")
    if task_model.status == EscrowStatus.FUNDED:
        task_model.complete = True    
        wallet_model = db.query(Wallet).filter(Wallet.owner_id==merchant_id.id).first()
        wallet_model.balance += task_model.amount
        task_model.status = EscrowStatus.RELEASED
        
        db.commit()
        return {
            "task_id": task_model.task_id,
            "merchant_id": task_model.merchant,
            "details": "Task completed successfully"
        }
    else:
        raise HTTPException(403, "wallet not funded")