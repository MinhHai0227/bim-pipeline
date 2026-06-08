from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IfcAssetCleaningChange(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    field: str
    from_: Any = Field(default=None, alias="from")
    to: Any = None
    rule: str


class IfcElementAsset(BaseModel):
    id: int
    ifc_file_id: int
    ifc_element_id: int | None
    asset_code: str | None
    global_id: str | None
    name: str | None
    tag: str | None
    ifc_class: str | None
    asset_type: str | None
    system_name: str | None
    floor: str | None
    room: str | None
    manufacturer: str | None
    model: str | None
    serial_number: str | None
    status: str | None
    material: dict | list | str | None
    cleaning_log: list[IfcAssetCleaningChange]


class IfcElementListItem(BaseModel):
    id: int
    ifc_file_id: int
    express_id: int | None
    global_id: str | None
    ifc_class: str | None
    name: str | None
    tag: str | None
    is_asset: bool


class IfcElementListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[IfcElementListItem]


class IfcElementDetailResponse(BaseModel):
    id: int
    ifc_file_id: int
    express_id: int | None
    global_id: str | None
    ifc_class: str | None
    name: str | None
    tag: str | None
    is_asset: bool
    floor: str | None
    room: str | None
    material: dict | list | str | None
    properties: dict[str, Any]
    quantities: dict[str, Any]
    raw_properties: dict[str, Any]
    asset: IfcElementAsset | None
