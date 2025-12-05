from fastapi import APIRouter, status
from services.escrow import (create_milestone_transaction, 
                             #create_milestone,
                             get_transaction_by_id, 
                             get_transaction_history, 
                             create_transaction,
                             client_confirm_milestone,
                             cancel_transaction,
                             client_confirm_transaction,
                             client_release_funds,
                             update_transactions,
                             dispute_transaction,
                             )

router = APIRouter(
    prefix="/escrow",
    tags=["escrow"]
)

router.get("/get_all_transactions", status_code=status.HTTP_200_OK)(get_transaction_history)

router.get("/get_transaction", status_code=status.HTTP_200_OK)(get_transaction_by_id)

router.post("/create_transaction", status_code=status.HTTP_201_CREATED)(create_transaction)

router.post("/create_milestone", status_code=status.HTTP_201_CREATED)(create_milestone_transaction)

router.post("/client_confirm_milestone", status_code=status.HTTP_200_OK)(client_confirm_milestone)

router.post("/client_release_funds", status_code=status.HTTP_200_OK)(client_release_funds)

router.post("/client_confirm", status_code=status.HTTP_200_OK)(client_confirm_transaction)

router.delete("/cancel_transaction", status_code=status.HTTP_200_OK)(cancel_transaction)

router.post("/dispute_transaction", status_code=status.HTTP_200_OK)(dispute_transaction)    



