from pydantic import BaseModel


class IfcViewerModelResponse(BaseModel):
    file_id: int
    status: str | None
    format: str | None
    storage_key: str | None
    size: int | None
    url: str | None
    error: str | None
