from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base
from src.models.enums import IfcFileStatus

if TYPE_CHECKING:
    from src.models.asset import Asset
    from src.models.ifc_element import IfcElement
    from src.models.validation_issue import ValidationIssue


class IfcFile(Base):
    __tablename__ = "ifc_files"
    __table_args__ = (
        Index("ix_ifc_files_status", "status"),
        Index("ix_ifc_files_created_at", "created_at"),
        Index("ix_ifc_files_source_format", "source_format"),
        Index("ix_ifc_files_normalization_status", "normalization_status"),
        Index("ix_ifc_files_viewer_model_status", "viewer_model_status"),
        Index("ix_ifc_files_pipeline_stage", "pipeline_stage"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    bucket_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255))
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    source_format: Mapped[str] = mapped_column(String(16), nullable=False, default="ifc")
    normalized_ifc_storage_key: Mapped[str | None] = mapped_column(String(1024))
    normalized_ifc_filename: Mapped[str | None] = mapped_column(String(255))
    normalized_ifc_size: Mapped[int | None] = mapped_column(BigInteger)
    normalization_status: Mapped[str | None] = mapped_column(String(32))
    normalization_error: Mapped[str | None] = mapped_column(Text)
    autodesk_activity_id: Mapped[str | None] = mapped_column(String(255))
    autodesk_workitem_id: Mapped[str | None] = mapped_column(String(128))
    viewer_model_key: Mapped[str | None] = mapped_column(String(1024))
    viewer_model_format: Mapped[str | None] = mapped_column(String(32))
    viewer_model_status: Mapped[str | None] = mapped_column(String(32))
    viewer_model_size: Mapped[int | None] = mapped_column(BigInteger)
    viewer_model_error: Mapped[str | None] = mapped_column(Text)
    pipeline_stage: Mapped[str | None] = mapped_column(String(64))
    pipeline_progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pipeline_message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[IfcFileStatus] = mapped_column(
        Enum(
            IfcFileStatus,
            name="ifc_file_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=IfcFileStatus.UPLOADED,
    )
    schema_name: Mapped[str | None] = mapped_column(String(64))
    total_elements: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_assets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_issues: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
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

    assets: Mapped[list["Asset"]] = relationship(
        "Asset",
        back_populates="ifc_file",
        cascade="all, delete-orphan",
    )
    elements: Mapped[list["IfcElement"]] = relationship(
        "IfcElement",
        back_populates="ifc_file",
        cascade="all, delete-orphan",
    )
    validation_issues: Mapped[list["ValidationIssue"]] = relationship(
        "ValidationIssue",
        back_populates="ifc_file",
        cascade="all, delete-orphan",
    )
