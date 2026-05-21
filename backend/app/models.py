from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class TriangleValueType(StrEnum):
    paid = "paid"
    incurred = "incurred"
    reported_claim_count = "reported_claim_count"
    earned_premium = "earned_premium"


class TriangleBasis(StrEnum):
    cumulative = "cumulative"
    incremental = "incremental"


class RunStatus(StrEnum):
    completed = "completed"
    failed = "failed"


class ExportType(StrEnum):
    excel = "excel"
    pdf = "pdf"


class ReviewStatus(StrEnum):
    draft = "draft"
    in_review = "in_review"
    approved = "approved"


class Organization(BaseModel):
    id: str
    name: str
    created_at: datetime = Field(default_factory=now_utc)


class User(BaseModel):
    id: str
    organization_id: str
    email: str
    name: str
    role: str = "actuary"
    created_at: datetime = Field(default_factory=now_utc)


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class Project(ProjectCreate):
    id: str = Field(default_factory=lambda: new_id("proj"))
    organization_id: str
    created_by: str
    review_status: ReviewStatus = ReviewStatus.draft
    created_at: datetime = Field(default_factory=now_utc)


class SystemStatus(BaseModel):
    database_backend: str
    database_url: str
    persistence: str = "database"


class Dataset(BaseModel):
    id: str = Field(default_factory=lambda: new_id("data"))
    organization_id: str
    project_id: str
    filename: str
    value_type: TriangleValueType
    triangle_basis: TriangleBasis = TriangleBasis.cumulative
    origin_column: str
    development_columns: list[str]
    raw_file_path: str
    created_by: str
    created_at: datetime = Field(default_factory=now_utc)


class Triangle(BaseModel):
    id: str = Field(default_factory=lambda: new_id("tri"))
    organization_id: str
    dataset_id: str
    origin_periods: list[str]
    development_periods: list[str]
    values: list[list[float | None]]
    source_values: list[list[float | None]] = Field(default_factory=list)
    triangle_basis: TriangleBasis = TriangleBasis.cumulative
    is_cumulative: bool = True
    validation_warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)


class TriangleDetail(BaseModel):
    dataset_id: str
    triangle_id: str
    triangle_basis: TriangleBasis
    origin_periods: list[str]
    development_periods: list[str]
    source_values: list[list[float | None]]
    values: list[list[float | None]]
    validation_warnings: list[str]


class ValidationResult(BaseModel):
    dataset_id: str
    triangle_id: str
    valid: bool
    warnings: list[str]
    origin_periods: int
    development_periods: int


class RunCreate(BaseModel):
    method: str = "chain_ladder"
    assumption_name: str = "Default chain ladder"
    selected_factors: list[float] | None = None
    exposure_values: list[float] | None = None
    expected_loss_ratio: float | None = None
    trend: float = 0
    decay: float = 1


class AssumptionSet(BaseModel):
    id: str = Field(default_factory=lambda: new_id("assump"))
    organization_id: str
    dataset_id: str
    name: str
    method: str
    selected_factors: list[float] | None = None
    exposure_values: list[float] | None = None
    expected_loss_ratio: float | None = None
    trend: float = 0
    decay: float = 1
    created_by: str
    created_at: datetime = Field(default_factory=now_utc)


class ReservingResult(BaseModel):
    latest_diagonal: list[float]
    age_to_age_factors: list[float]
    cumulative_development_factors: list[float]
    link_ratio_triangle: list[list[float | None]] = Field(default_factory=list)
    projected_cumulative_triangle: list[list[float | None]] = Field(default_factory=list)
    incremental_triangle: list[list[float | None]] = Field(default_factory=list)
    factor_diagnostics: list[dict[str, Any]] = Field(default_factory=list)
    ultimate_by_origin: list[float]
    ibnr_by_origin: list[float]
    total_latest: float
    total_ultimate: float
    total_ibnr: float
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class ModelRun(BaseModel):
    id: str = Field(default_factory=lambda: new_id("run"))
    organization_id: str
    project_id: str
    dataset_id: str
    triangle_id: str
    assumption_set_id: str
    method: str
    status: RunStatus
    result: ReservingResult
    created_by: str
    created_at: datetime = Field(default_factory=now_utc)


class SelectionCreate(BaseModel):
    selected_factors: list[float] | None = None
    selected_ultimates: list[float] | None = None
    reason: str
    comment: str | None = None


class Selection(SelectionCreate):
    id: str = Field(default_factory=lambda: new_id("sel"))
    organization_id: str
    run_id: str
    created_by: str
    created_at: datetime = Field(default_factory=now_utc)


class ReviewCommentCreate(BaseModel):
    body: str


class ReviewComment(ReviewCommentCreate):
    id: str = Field(default_factory=lambda: new_id("comment"))
    organization_id: str
    project_id: str
    run_id: str | None = None
    created_by: str
    created_at: datetime = Field(default_factory=now_utc)


class ExportCreate(BaseModel):
    export_type: ExportType


class ExportJob(BaseModel):
    id: str = Field(default_factory=lambda: new_id("export"))
    organization_id: str
    run_id: str
    export_type: ExportType
    status: str = "completed"
    file_path: str
    created_by: str
    created_at: datetime = Field(default_factory=now_utc)


class AuditEvent(BaseModel):
    id: str = Field(default_factory=lambda: new_id("audit"))
    organization_id: str
    project_id: str | None = None
    actor_id: str
    event_type: str
    entity_type: str
    entity_id: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now_utc)
