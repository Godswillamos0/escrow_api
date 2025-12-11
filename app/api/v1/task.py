from fastapi import APIRouter, status
from services.task import (get_task_by_id,
                           client_get_all_task,
                           merchant_get_all_task,
                           save_task,
                             )

router = APIRouter(
    prefix="/task",
    tags=["task"]
)

router.get("/pay_task", status_code=status.HTTP_200_OK)(save_task)

router.get("/client_get_all_task", status_code=status.HTTP_200_OK)(client_get_all_task)

router.post("/merchant_get_all_task", status_code=status.HTTP_201_CREATED)(merchant_get_all_task)

router.post("/get_task_by_id", status_code=status.HTTP_201_CREATED)(get_task_by_id)  



