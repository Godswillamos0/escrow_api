from pydantic import EmailStr, BaseModel
from typing import Optional


class CreateUser(BaseModel):
    id: Optional[str] #id from the source
    email: EmailStr
    
    
class AddWithdrawalBank(BaseModel):
    user_id: str #id from the source
    bank_code: str
    bank_name: str
    account_number: str
    account_name: Optional[str] = None
    

    