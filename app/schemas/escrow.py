from pydantic import EmailStr, BaseModel, Field
from typing import Optional, Any, List
from datetime import datetime
from decimal import Decimal


class UserConfirmation(BaseModel):
    project_id: str #id from the source
    user_id: str #id from the source
    confirm_status: bool = Field(default=False)
    milestone_key: Optional[str] = Field(default=None)
    
    
class UserConfirmMilestone(BaseModel):
    project_id: str #id from the source
    user_id: str #id from the source
    milestone_key: str
    confirm_status: bool = Field(default=False)
    title: str
    description: str
    amount: Decimal= Field(gt=0.00)
 

class Milestone(BaseModel):
    key: str
    milestone_name: str
    description: Optional[str] = None
    amount: Decimal = Field(gt=0.00)
    
class UpdateMilestone(BaseModel):
    milestone_id: str
    milestone_name: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[Decimal] = Field(None, gt=0.00)
    
class DeleteMilestone(BaseModel):
    milestone_id: str
    project_id: str

class TransactionMilestoneInstance(BaseModel):
    merchant_id: str #id from the source
    client_id: str #id from the source
    project_id: str #id from the source
    amount: Decimal = Field(gt=0.00)
    milestone: Optional[List[Milestone]]
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "merchant_id": "merchant_id",
                "client_id": "client_id",
                "project_id": "project_id",
                "amount": 100.00,
                "milestone": []
            }
        }
    }
    
    
class TransactionInstance(BaseModel):
    merchant_id: str #id from the source
    client_id: str #id from the source
    project_id: str #id from the source
    amount: Decimal = Field(gt=0.00)
    
    
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
        
    