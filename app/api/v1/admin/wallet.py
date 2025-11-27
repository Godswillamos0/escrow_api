from fastapi import HTTPException, status, Query, Path, APIRouter
from services.admin.wallet import (
    get_wallet_transactions,
    freeze_wallet,
    unfreeze_wallet,
    debit_wallet,
    credit_wallet,
    get_wallet_by_user_id,
    get_all_wallets
)
    

router = APIRouter(
    prefix="/wallet",
    tags=["wallet"]
)


router.post("/credit", status_code=status.HTTP_200_OK)(credit_wallet)

router.post("/debit", status_code=status.HTTP_200_OK)(debit_wallet)

router.get("/get_transactions", status_code=status.HTTP_200_OK)(get_wallet_transactions)

router.get("/get_wallet", status_code=status.HTTP_200_OK)(get_wallet_by_user_id)

#post request
router.post("/freeze", status_code=status.HTTP_200_OK)(freeze_wallet)

router.post("/unfreeze", status_code=status.HTTP_200_OK)(unfreeze_wallet)

router.get("/get_all_wallets", status_code=status.HTTP_200_OK)(get_all_wallets)


