from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.models.ifc_element import IfcElement
    from src.models.ifc_file import IfcFile
    from src.models.validation_issue import ValidationIssue


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("ifc_element_id", name="uq_assets_ifc_element_id"),
        Index("ix_assets_file_id", "ifc_file_id"),
        Index("ix_assets_ifc_element_id", "ifc_element_id"),
        Index("ix_assets_global_id", "global_id"),
        Index("ix_assets_asset_code", "asset_code"),
        Index("ix_assets_ifc_class", "ifc_class"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ifc_file_id: Mapped[int] = mapped_column(
        ForeignKey("ifc_files.id", ondelete="CASCADE"),
        nullable=False,
    )
    ifc_element_id: Mapped[int | None] = mapped_column(
        ForeignKey("ifc_elements.id", ondelete="SET NULL"),
    )
    asset_code: Mapped[str | None] = mapped_column(String(255))
    global_id: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str | None] = mapped_column(String(512))
    tag: Mapped[str | None] = mapped_column(String(255))
    ifc_class: Mapped[str | None] = mapped_column(String(128))
    asset_type: Mapped[str | None] = mapped_column(String(128))
    system_name: Mapped[str | None] = mapped_column(String(255))
    floor: Mapped[str | None] = mapped_column(String(255))
    room: Mapped[str | None] = mapped_column(String(255))
    manufacturer: Mapped[str | None] = mapped_column(String(255))
    model: Mapped[str | None] = mapped_column(String(255))
    serial_number: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str | None] = mapped_column(String(64))
    material: Mapped[dict | list | str | None] = mapped_column(JSONB)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    quantities: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    raw_properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    ifc_file: Mapped["IfcFile"] = relationship("IfcFile", back_populates="assets")
    ifc_element: Mapped["IfcElement | None"] = relationship(
        "IfcElement",
        back_populates="asset",
    )
    validation_issues: Mapped[list["ValidationIssue"]] = relationship(
        "ValidationIssue",
        back_populates="asset",
    )
