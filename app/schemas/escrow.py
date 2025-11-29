from pydantic import EmailStr, BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from decimal import Decimal


class UserConfirmation(BaseModel):
    project_id: str #id from the source
    user_id: str #id from the source
    escrow_id: str #id of the escrow
    confirm_status: bool = Field(default=False)
    
    
class TransactionInstance(BaseModel):
    merchant_id: str #id from the source
    client_id: str #id from the source
    project_id: str #id from the source
    amount: float = Field(gt=0.00)
    
    
class ReleaseFunds(BaseModel):
    project_id: str
    user_id: str #id from the source
    
    
class CancelRequest(BaseModel):
    user_id: str
    project_id: str
    
    
class DisputeRequest(BaseModel):
    project_id: str
    user_id: str #id from the source
    reason: Optional[str] = None


class EscrowResponse(BaseModel):
    id: str
    client_id: str
    merchant_id: str
    client_agree: bool
    merchant_agree: bool
    amount: Decimal
    status: Any  # Using Any for Enum, can be more specific
    created_at: datetime
    finalized_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        
    