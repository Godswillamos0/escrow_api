from fastapi import APIRouter, status
from services.admin.escrow import (
    force_release_funds,
    force_return_funds,
    get_all_disputed_transactions,
    get_all_transactions,
    get_escrow_by_id,
    cancel_transaction,
    dispute_transaction
)
router = APIRouter(
    prefix="/escrow",
    tags=["escrow"]
)

router.get("/get_all_transactions", status_code=status.HTTP_200_OK)(get_all_transactions)

router.get("/get_escrow_by_id", status_code=status.HTTP_200_OK)(get_escrow_by_id)

router.post("/cancel_transaction", status_code=status.HTTP_200_OK)(cancel_transaction)

router.post("/dispute_transaction", status_code=status.HTTP_200_OK)(dispute_transaction)

router.get("/get_all_disputed_transactions", status_code=status.HTTP_200_OK)(get_all_disputed_transactions)

router.post("/force_release_funds", status_code=status.HTTP_200_OK)(force_release_funds)

router.post("/force_return_funds", status_code=status.HTTP_200_OK)(force_return_funds)






