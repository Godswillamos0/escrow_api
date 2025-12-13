from fastapi import APIRouter, status
from services.task import (complete_task,
                           save_task,
                             )

router = APIRouter(
    prefix="/task",
    tags=["task"]
)

router.post("/pay", status_code=status.HTTP_200_OK)(save_task)

router.post("/complete", status_code=status.HTTP_200_OK)(complete_task)