from fastapi import APIRouter, status
from services.paystack_handler import paystack_webhook_handler as pwd


router = APIRouter(
    prefix="/paystack",
    tags=["paystack"]
)


router.post("/webhook", status_code=status.HTTP_200_OK)(pwd)