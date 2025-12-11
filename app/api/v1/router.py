from fastapi import APIRouter
from . import (
    escrow,
    paystack,
    wallet,
    bank,
    task
)
from .admin import router as admin_router


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

router.include_router(
    admin_router.router
)

router.include_router(
    task.router
)