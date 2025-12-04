from pydantic import EmailStr, BaseModel, Field
from typing import Optional, Any, List
from datetime import datetime
from decimal import Decimal


class UserConfirmation(BaseModel):
    project_id: str #id from the source
    user_id: str #id from the source
    confirm_status: bool = Field(default=False)
    

class Milestone(BaseModel):
    project_id: str
    milestone_name: str
    description: Optional[str] = None
    amount: float = Field(gt=0.00)
    due_date: datetime
    
class UpdateMilestone(BaseModel):
    milestone_id: str
    milestone_name: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0.00)
    due_date: Optional[datetime] = None
    
class DeleteMilestone(BaseModel):
    milestone_id: str
    project_id: str

class TransactionInstance(BaseModel):
    merchant_id: str #id from the source
    client_id: str #id from the source
    project_id: str #id from the source
    amount: float = Field(gt=0.00)
    milestone: List[dict]
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "merchant_id": "merchant_id",
                "client_id": "client_id",
                "project_id": "project_id",
                "amount": 100.00,
                "milestone": [
                    {
                        "milestone_name": "Milestone 1",
                        "description": "Description for Milestone 1",
                        "amount": 50.00,
                        "due_date": "2023-09-30T00:00:00"
                    },
                    {
                        "milestone_name": "Milestone 2",
                        "description": "Description for Milestone 2",
                        "amount": 30.00,
                        "due_date": "2023-10-15T00:00:00"
                    }
                ]
            }
        }
    }
    
    
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
        
    