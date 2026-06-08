from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DigitalTwinCleaningChange(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    field: str
    from_: Any = Field(default=None, alias="from")
    to: Any = None
    rule: str


class DigitalTwinAssetResponse(BaseModel):
    id: int
    ifc_file_id: int
    ifc_element_id: int | None
    global_id: str | None
    asset_id: str | None
    asset_name: str | None
    asset_type: str | None
    ifc_class: str | None
    system: str | None
    location: str | None
    floor: str | None
    room_zone: str | None
    manufacturer: str | None
    model: str | None
    serial_number: str | None
    status: str | None
    cleaning_log: list[DigitalTwinCleaningChange]


class DigitalTwinAssetListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[DigitalTwinAssetResponse]
