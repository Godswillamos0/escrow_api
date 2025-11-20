from fastapi import APIRouter, status
from . import (
    escrow,
    wallet,
)

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

router.include_router(
    escrow.router
)

router.include_router(
    wallet.router
)