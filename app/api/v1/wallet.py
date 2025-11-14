from fastapi import APIRouter, status
from services.wallet import (create_wallet, 
                             withdraw_funds, 
                             add_funds_to_wallet, 
                             get_balance, 
                             transaction_history)
from services.paystack_handler import initialize_payment


router = APIRouter(
    prefix="/wallet",
    tags=["wallet"]
)


router.post("/create", status_code=status.HTTP_200_OK)(create_wallet)

router.post("/fund", status_code=status.HTTP_200_OK)(initialize_payment) #(add_funds_to_wallet)

router.post("/withdraw", status_code=status.HTTP_200_OK)(withdraw_funds)

router.get("/balance", status_code=status.HTTP_200_OK)(get_balance)

router.get("/transaction_history", status_code=status.HTTP_200_OK)(transaction_history)