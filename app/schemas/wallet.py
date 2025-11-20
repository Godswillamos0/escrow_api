from pydantic import EmailStr, BaseModel, Field, conint
from typing import Optional
from datetime import datetime
from db.models import CurrencyCode, TransactionType


class WalletRequestDTO(BaseModel):
    user_id: str
    email: EmailStr
    currency: Optional[CurrencyCode]
    created_at: datetime
    
    """model_config : dict = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": "string",
                    "email": "string",
                }
            ]
        }
    }"""
    
    
class TransactionRequestDTO(BaseModel):
    user_id: str
    email: EmailStr
    currency: Optional[CurrencyCode]
    amount: float = Field(gt=100.00)
    transaction_type: Optional[TransactionType]
    time: datetime
    reason: Optional[str] = None
    
    
class PaymentMetadata(BaseModel):
    user_id: str #id from the source
    wallet_id: Optional[str] = None
    

class PaymentRequest(BaseModel): 
    email: EmailStr
    amount: float= Field(gt=0)  # positive integer, in kobo
    metadata: Optional[PaymentMetadata] = None
    
    
    
    
    
    
    
    
    
    