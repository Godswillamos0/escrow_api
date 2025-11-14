import json
from datetime import datetime, timedelta
from fastapi import HTTPException, Query, Request
from db.models import User, WithdrawalBank
from schemas.bank import AddWithdrawalBank
from db.dependencies import db_dependency
from utils.paystack_bank_utils import (
    resolve_bank_account,
    get_all_banks_from_paystack,
)
from utils.mail_config import send_mail
from utils.redis_config import (
    get_key,
    set_key
)
    

async def add_withdrawal_account(
    db: db_dependency,
    withdrawal_account: AddWithdrawalBank
):
    user_model = db.query(User).filter(User.source_id == withdrawal_account.user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="User not found")
    
    withdrawal_account_model = WithdrawalBank(
        owner_id = user_model.id,
        bank_code = withdrawal_account.bank_code,
        bank_name = withdrawal_account.bank_name,
        account_number = withdrawal_account.account_number,
        account_name = withdrawal_account.account_name
    )
    db.add(withdrawal_account_model)
    db.commit()
    db.refresh(withdrawal_account_model)
    
    send_mail(
        email=user_model.email,
        subject="Withdrawal Bank Added",
        body= f'''
        You just added a withdrawal bank.
        Bank Code: {withdrawal_account.bank_code} 
        Account Number: {withdrawal_account.account_number}
        Bank Name: {withdrawal_account.bank_name}
        '''
    )
    
    return {
        "id": withdrawal_account_model.id,
        "bank_code": withdrawal_account_model.bank_code,
        "account_number": withdrawal_account_model.account_number,
        "owner_id": user_model.source_id,
        "message": "Withdrawal bank added successfully"
    }
    

async def get_withdrawal_accounts(
    db: db_dependency,
    user_id = Query(...)
):
    # get from redis
    
    
    user_model = db.query(User).filter(User.source_id == user_id).first()

    if not user_model:
        raise HTTPException(status_code=404, detail="User not found")

    withdrawal_accounts = user_model.banks
    
    return [
        {
            "id": bank.id,
            "bank_code": bank.bank_code,
            "account_number": bank.account_number,
            "owner_id": user_model.source_id
        }
        for bank in withdrawal_accounts
    ]


async def get_withdrawal_account_by_id(
    db: db_dependency,
    withdrawal_account_id = Query(...)
):
    #get from redis
    
    withdrawal_account_model = db.query(WithdrawalBank).filter(WithdrawalBank.id == withdrawal_account_id).first()
    if not withdrawal_account_model:
        raise HTTPException(status_code=404, detail="Withdrawal bank not found")        
    
    return {
        "id": withdrawal_account_model.id,
        "bank_code": withdrawal_account_model.bank_code,
        "bank_name": withdrawal_account_model.bank_name,
        "account_number": withdrawal_account_model.account_number,
        "owner_id": withdrawal_account_model.owner_id
    }
    
    
async def delete_withdrawal_account(
    db: db_dependency,
    withdrawal_account_id = Query(...)
):
    withdrawal_account_model = db.query(WithdrawalBank).filter(WithdrawalBank.id == withdrawal_account_id).first()
    if not withdrawal_account_model:
        raise HTTPException(status_code=404, detail="Withdrawal bank not found")
    
    db.delete(withdrawal_account_model)
    db.commit()
    
    
async def get_all_banks(request: Request):
    # check redis
    banks = await get_key(request=request,
                          key = "banks")
    if not banks:
        banks = await get_all_banks_from_paystack()
        await set_key("banks", json.dumps(banks), timedelta(hours=2), request)
    else:
        # decode JSON only if Redis returned a string
        if isinstance(banks, str):
            banks = json.loads(banks)
    
    return [
        {
            "bank_code": bank_detail.get("bank_code"),
            "name": bank_detail.get("name"),
        }
        for bank_detail in banks]
    
    
async def confirm_withdrawal_account(
    withdrawal_account: AddWithdrawalBank,
    request: Request
):
    # Extract from redis
    account_name = await get_key(f"{withdrawal_account.bank_code}:{withdrawal_account.account_number}",
                                 request=request)
    
    if not account_name:
        account_details = await resolve_bank_account(
            account_number=withdrawal_account.account_number,
            bank_code=withdrawal_account.bank_code
        )
        
        if not account_details:
            print(account_details)
            raise HTTPException(status_code=400, detail="Invalid bank account details")
        
        account_name = account_details.get("account_name")
        #add to redis
        set_key(key = f"{withdrawal_account.bank_code}:{withdrawal_account.account_number}", 
                value=account_name,
                exp=timedelta(hours=1),
                request=request)
    
    return {
        "account_name": account_name,
    }
    
    

    



    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    