from pydantic import BaseModel

from src.models.enums import IfcFileStatus


class IfcImportQueuedResponse(BaseModel):
    file_id: int
    filename: str
    status: IfcFileStatus
    storage_key: str
    bucket_name: str
    celery_task_id: str
