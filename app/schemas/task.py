from pydantic import EmailStr, BaseModel, Field
from typing import Optional, Any, List
from decimal import Decimal
from datetime import datetime


class CreateTask(BaseModel):
    title: str = Field(min_length=3, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    due_date: Optional[datetime] = None
    amount: Decimal = Field(gt=0.00)
    task_id: str
    client_id: str
    merchant_id: str

class UpdateTask(BaseModel):
    task_id: str
    title: Optional[str] = Field(None, min_length=3, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    due_date: Optional[str] = None
    amount: Optional[Decimal] = Field(None, gt=0.00)

class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    due_date: Optional[str]
    amount: Decimal
    status: Any
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        
class GetTaskRequest(BaseModel):
    task_id: str
