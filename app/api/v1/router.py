from fastapi import APIRouter
from . import (
    escrow,
    paystack,
    wallet,
    bank
)

router = APIRouter(
    prefix="/api"
)

router.include_router(
    escrow.router
)

router.include_router(
    paystack.router
)

router.include_router(
    wallet.router
)

router.include_router(
    bank.router
)