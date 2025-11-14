from fastapi import APIRouter
from services.bank import (
    add_withdrawal_account,
    get_withdrawal_accounts,
    get_withdrawal_account_by_id,
    delete_withdrawal_account,
    confirm_withdrawal_account,
    get_all_banks,
)

router = APIRouter(
    prefix="/bank",
    tags= ["bank"]
)


router.post("/withdrawal_account", status_code=200)(add_withdrawal_account)

router.get("/get_withdrawal_account", status_code=200)(get_withdrawal_accounts)

router.get("/withdrawal_account", status_code=200)(get_withdrawal_account_by_id)

router.delete("/withdrawal_account", status_code=202)(delete_withdrawal_account)

router.get("/get_all_accounts", status_code=200)(get_all_banks)

router.post("/confirm_withdrawal_account", status_code=200)(confirm_withdrawal_account)


