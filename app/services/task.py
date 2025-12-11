from fastapi import HTTPException, status, Path
from db.dependencies import db_dependency
from db.models import Task, User, Wallet
from datetime import datetime
from decimal import Decimal
from schemas.task import (CreateTask, UpdateTask)


async def save_task(
    db: db_dependency,
    task: CreateTask
):
    task_model = CreateTask(**task)
    
    db.add(task_model)
    db.flush()
    
    #withdraw from client_id
    client_id = db.query(User).filter(User.id == task.client_id).first()
    merchant_id = db.query(User).filter(User.id == task.merchant_id).first()
    if not (client_id and merchant_id):
        raise HTTPException(404, "User not found.")
    
    wallet_model = db.query(Wallet).filter(Wallet.owner_id==client_id.id).first()
    
    wallet_model.balance -= task_model.amount
    
    db.commit()
    
    return {
        "detail": "Task created successfully"
    }
    
async def client_get_all_task(
    db: db_dependency,
    user_id = Path(...) 
):
    user_model = db.query(User).filter(User.source_id == user_id).first()
    if not user_model:
        raise HTTPException(404, "User not found")
    
    tasks = db.query(Task).filter(Task.client == user_model.id).all()
    
    return tasks


async def merchant_get_all_task(
    db: db_dependency,
    user_id = Path(...) 
):
    user_model = db.query(User).filter(User.source_id == user_id).first()
    if not user_model:
        raise HTTPException(404, "User not found")
    
    tasks = db.query(Task).filter(Task.merchant == user_model.id).all()
    
    return tasks

async def get_task_by_id(
    db: db_dependency,
    task_id = Path(...)
):
   task = db.query(Task).filter(Task.task_id == task_id).first()
   if not task:
       raise HTTPException(404, "Task not found")
   
   return task

