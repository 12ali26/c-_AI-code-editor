from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class OrganizationRow(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectRow(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(80), nullable=False)
    review_status: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DatasetRow(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    value_type: Mapped[str] = mapped_column(String(80), nullable=False)
    triangle_basis: Mapped[str] = mapped_column(String(80), nullable=False)
    origin_column: Mapped[str] = mapped_column(String(255), nullable=False)
    development_columns: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    raw_file_path: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TriangleRow(Base):
    __tablename__ = "triangles"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), unique=True, index=True, nullable=False)
    origin_periods: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    development_periods: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    values: Mapped[list[list[float | None]]] = mapped_column(JSON, nullable=False)
    source_values: Mapped[list[list[float | None]]] = mapped_column(JSON, nullable=False)
    triangle_basis: Mapped[str] = mapped_column(String(80), nullable=False)
    is_cumulative: Mapped[bool] = mapped_column(Boolean, nullable=False)
    validation_warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AssumptionSetRow(Base):
    __tablename__ = "assumption_sets"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    method: Mapped[str] = mapped_column(String(80), nullable=False)
    selected_factors: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    exposure_values: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    expected_loss_ratio: Mapped[float | None] = mapped_column(JSON, nullable=True)
    trend: Mapped[float] = mapped_column(JSON, nullable=False)
    decay: Mapped[float] = mapped_column(JSON, nullable=False)
    created_by: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ModelRunRow(Base):
    __tablename__ = "model_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True, nullable=False)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True, nullable=False)
    triangle_id: Mapped[str] = mapped_column(ForeignKey("triangles.id"), nullable=False)
    assumption_set_id: Mapped[str] = mapped_column(String(80), nullable=False)
    method: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_by: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SelectionRow(Base):
    __tablename__ = "selections"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    run_id: Mapped[str] = mapped_column(ForeignKey("model_runs.id"), index=True, nullable=False)
    selected_factors: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    selected_ultimates: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExportJobRow(Base):
    __tablename__ = "export_jobs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    run_id: Mapped[str] = mapped_column(ForeignKey("model_runs.id"), index=True, nullable=False)
    export_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    actor_id: Mapped[str] = mapped_column(String(80), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(80), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

