from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.models.asset import Asset
    from src.models.ifc_file import IfcFile
    from src.models.validation_issue import ValidationIssue


class IfcElement(Base):
    __tablename__ = "ifc_elements"
    __table_args__ = (
        UniqueConstraint(
            "ifc_file_id",
            "express_id",
            name="uq_ifc_elements_file_express_id",
        ),
        Index("ix_ifc_elements_file_id", "ifc_file_id"),
        Index("ix_ifc_elements_global_id", "global_id"),
        Index("ix_ifc_elements_express_id", "express_id"),
        Index("ix_ifc_elements_ifc_class", "ifc_class"),
        Index("ix_ifc_elements_name", "name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ifc_file_id: Mapped[int] = mapped_column(
        ForeignKey("ifc_files.id", ondelete="CASCADE"),
        nullable=False,
    )
    express_id: Mapped[int | None] = mapped_column(Integer)
    global_id: Mapped[str | None] = mapped_column(String(64))
    ifc_class: Mapped[str | None] = mapped_column(String(128))
    name: Mapped[str | None] = mapped_column(String(512))
    tag: Mapped[str | None] = mapped_column(String(255))
    floor: Mapped[str | None] = mapped_column(String(255))
    room: Mapped[str | None] = mapped_column(String(255))
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

    ifc_file: Mapped["IfcFile"] = relationship(
        "IfcFile",
        back_populates="elements",
    )
    asset: Mapped["Asset | None"] = relationship(
        "Asset",
        back_populates="ifc_element",
        uselist=False,
    )
    validation_issues: Mapped[list["ValidationIssue"]] = relationship(
        "ValidationIssue",
        back_populates="ifc_element",
    )
