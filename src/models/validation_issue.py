from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base
from src.models.enums import ValidationSeverity, ValidationStage

if TYPE_CHECKING:
    from src.models.asset import Asset
    from src.models.ifc_element import IfcElement
    from src.models.ifc_file import IfcFile


class ValidationIssue(Base):
    __tablename__ = "validation_issues"
    __table_args__ = (
        Index("ix_validation_issues_file_id", "ifc_file_id"),
        Index("ix_validation_issues_asset_id", "asset_id"),
        Index("ix_validation_issues_ifc_element_id", "ifc_element_id"),
        Index("ix_validation_issues_stage", "stage"),
        Index("ix_validation_issues_severity", "severity"),
        Index("ix_validation_issues_code", "code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ifc_file_id: Mapped[int] = mapped_column(
        ForeignKey("ifc_files.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"),
    )
    ifc_element_id: Mapped[int | None] = mapped_column(
        ForeignKey("ifc_elements.id", ondelete="SET NULL"),
    )
    global_id: Mapped[str | None] = mapped_column(String(64))
    ifc_class: Mapped[str | None] = mapped_column(String(128))
    object_name: Mapped[str | None] = mapped_column(String(512))
    stage: Mapped[ValidationStage] = mapped_column(
        Enum(
            ValidationStage,
            name="validation_stage",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )
    severity: Mapped[ValidationSeverity] = mapped_column(
        Enum(
            ValidationSeverity,
            name="validation_severity",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    field: Mapped[str | None] = mapped_column(String(128))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    ifc_file: Mapped["IfcFile"] = relationship(
        "IfcFile",
        back_populates="validation_issues",
    )
    asset: Mapped["Asset | None"] = relationship(
        "Asset",
        back_populates="validation_issues",
    )
    ifc_element: Mapped["IfcElement | None"] = relationship(
        "IfcElement",
        back_populates="validation_issues",
    )
