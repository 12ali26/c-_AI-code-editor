from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile

from app.models import (
    AssumptionSet,
    AuditEvent,
    Dataset,
    ExportCreate,
    ExportJob,
    ModelRun,
    Project,
    ProjectCreate,
    RunCreate,
    RunStatus,
    Selection,
    SelectionCreate,
    TriangleValueType,
    ValidationResult,
)
from app.repository import InMemoryRepository, NotFoundError, TenantAccessError, repo
from app.services.exports import create_export
from app.services.reserving import ReservingError, run_bornhuetter_ferguson, run_cape_cod, run_chain_ladder
from app.services.triangle import TriangleParseError, parse_triangle_file, validation_summary

router = APIRouter(prefix="/api/v1")


class Principal:
    def __init__(self, organization_id: str, user_id: str) -> None:
        self.organization_id = organization_id
        self.user_id = user_id


async def get_repo() -> InMemoryRepository:
    return repo


async def get_principal(
    x_org_id: str = Header(default="demo-org"),
    x_user_id: str = Header(default="demo-user"),
    repository: InMemoryRepository = Depends(get_repo),
) -> Principal:
    repository.ensure_principal(x_org_id, x_user_id)
    return Principal(organization_id=x_org_id, user_id=x_user_id)


@router.post("/projects", response_model=Project)
async def create_project(
    payload: ProjectCreate,
    principal: Principal = Depends(get_principal),
    repository: InMemoryRepository = Depends(get_repo),
) -> Project:
    project = Project(
        organization_id=principal.organization_id,
        created_by=principal.user_id,
        **payload.model_dump(),
    )
    repository.add_project(project)
    repository.add_audit_event(
        AuditEvent(
            organization_id=principal.organization_id,
            project_id=project.id,
            actor_id=principal.user_id,
            event_type="project.created",
            entity_type="project",
            entity_id=project.id,
        )
    )
    return project


@router.post("/projects/{project_id}/datasets", response_model=Dataset)
async def upload_dataset(
    project_id: str,
    file: UploadFile = File(...),
    origin_column: str = "origin_period",
    value_type: TriangleValueType = TriangleValueType.paid,
    principal: Principal = Depends(get_principal),
    repository: InMemoryRepository = Depends(get_repo),
) -> Dataset:
    try:
        repository.get_project(project_id, principal.organization_id)
    except (NotFoundError, TenantAccessError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    content = await file.read()
    storage_root = Path(os.getenv("LOCAL_STORAGE_ROOT", "./storage")) / "uploads"
    storage_root.mkdir(parents=True, exist_ok=True)

    dataset = Dataset(
        organization_id=principal.organization_id,
        project_id=project_id,
        filename=file.filename or "triangle.csv",
        value_type=value_type,
        origin_column=origin_column,
        development_columns=[],
        raw_file_path="",
        created_by=principal.user_id,
    )
    raw_path = storage_root / f"{dataset.id}_{dataset.filename}"
    raw_path.write_bytes(content)
    dataset.raw_file_path = str(raw_path)

    try:
        development_columns, triangle = parse_triangle_file(
            content=content,
            filename=dataset.filename,
            organization_id=principal.organization_id,
            dataset_id=dataset.id,
            origin_column=origin_column,
            value_type=value_type,
        )
    except TriangleParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    dataset.development_columns = development_columns
    repository.add_dataset(dataset, triangle)
    repository.add_audit_event(
        AuditEvent(
            organization_id=principal.organization_id,
            project_id=project_id,
            actor_id=principal.user_id,
            event_type="dataset.uploaded",
            entity_type="dataset",
            entity_id=dataset.id,
            details={"filename": dataset.filename, "warnings": triangle.validation_warnings},
        )
    )
    return dataset


@router.post("/datasets/{dataset_id}/validate", response_model=ValidationResult)
async def validate_dataset(
    dataset_id: str,
    principal: Principal = Depends(get_principal),
    repository: InMemoryRepository = Depends(get_repo),
) -> ValidationResult:
    try:
        triangle = repository.get_triangle_for_dataset(dataset_id, principal.organization_id)
    except (NotFoundError, TenantAccessError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ValidationResult(**validation_summary(triangle))


@router.post("/datasets/{dataset_id}/runs", response_model=ModelRun)
async def create_model_run(
    dataset_id: str,
    payload: RunCreate,
    principal: Principal = Depends(get_principal),
    repository: InMemoryRepository = Depends(get_repo),
) -> ModelRun:
    try:
        dataset = repository.get_dataset(dataset_id, principal.organization_id)
        triangle = repository.get_triangle_for_dataset(dataset_id, principal.organization_id)
    except (NotFoundError, TenantAccessError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    assumption = AssumptionSet(
        organization_id=principal.organization_id,
        dataset_id=dataset_id,
        name=payload.assumption_name,
        method=payload.method,
        selected_factors=payload.selected_factors,
        exposure_values=payload.exposure_values,
        expected_loss_ratio=payload.expected_loss_ratio,
        trend=payload.trend,
        decay=payload.decay,
        created_by=principal.user_id,
    )
    try:
        if payload.method == "chain_ladder":
            result = run_chain_ladder(triangle, selected_factors=payload.selected_factors)
        elif payload.method == "bornhuetter_ferguson":
            if payload.exposure_values is None or payload.expected_loss_ratio is None:
                raise ReservingError(
                    "Bornhuetter-Ferguson requires exposure_values and expected_loss_ratio"
                )
            result = run_bornhuetter_ferguson(
                triangle,
                exposure_values=payload.exposure_values,
                expected_loss_ratio=payload.expected_loss_ratio,
                selected_factors=payload.selected_factors,
            )
        elif payload.method == "cape_cod":
            if payload.exposure_values is None:
                raise ReservingError("Cape Cod requires exposure_values")
            result = run_cape_cod(
                triangle,
                exposure_values=payload.exposure_values,
                selected_factors=payload.selected_factors,
                trend=payload.trend,
                decay=payload.decay,
            )
        else:
            raise ReservingError("Supported methods are chain_ladder, bornhuetter_ferguson, and cape_cod")
    except ReservingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    run = ModelRun(
        organization_id=principal.organization_id,
        project_id=dataset.project_id,
        dataset_id=dataset_id,
        triangle_id=triangle.id,
        assumption_set_id=assumption.id,
        method=payload.method,
        status=RunStatus.completed,
        result=result,
        created_by=principal.user_id,
    )
    repository.add_run(run)
    repository.add_audit_event(
        AuditEvent(
            organization_id=principal.organization_id,
            project_id=dataset.project_id,
            actor_id=principal.user_id,
            event_type="model_run.created",
            entity_type="model_run",
            entity_id=run.id,
            details={"method": run.method, "total_ibnr": run.result.total_ibnr},
        )
    )
    return run


@router.get("/runs/{run_id}", response_model=ModelRun)
async def get_run(
    run_id: str,
    principal: Principal = Depends(get_principal),
    repository: InMemoryRepository = Depends(get_repo),
) -> ModelRun:
    try:
        return repository.get_run(run_id, principal.organization_id)
    except (NotFoundError, TenantAccessError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/runs/{run_id}/selections", response_model=Selection)
async def create_selection(
    run_id: str,
    payload: SelectionCreate,
    principal: Principal = Depends(get_principal),
    repository: InMemoryRepository = Depends(get_repo),
) -> Selection:
    try:
        run = repository.get_run(run_id, principal.organization_id)
    except (NotFoundError, TenantAccessError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    selection = Selection(
        organization_id=principal.organization_id,
        run_id=run_id,
        created_by=principal.user_id,
        **payload.model_dump(),
    )
    repository.add_selection(selection)
    repository.add_audit_event(
        AuditEvent(
            organization_id=principal.organization_id,
            project_id=run.project_id,
            actor_id=principal.user_id,
            event_type="selection.created",
            entity_type="selection",
            entity_id=selection.id,
            details={"reason": selection.reason},
        )
    )
    return selection


@router.post("/runs/{run_id}/exports", response_model=ExportJob)
async def create_run_export(
    run_id: str,
    payload: ExportCreate,
    principal: Principal = Depends(get_principal),
    repository: InMemoryRepository = Depends(get_repo),
) -> ExportJob:
    try:
        run = repository.get_run(run_id, principal.organization_id)
        triangle = repository.get_triangle_for_dataset(run.dataset_id, principal.organization_id)
    except (NotFoundError, TenantAccessError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    file_path = create_export(run, triangle, payload.export_type, os.getenv("LOCAL_STORAGE_ROOT", "./storage"))
    export = ExportJob(
        organization_id=principal.organization_id,
        run_id=run_id,
        export_type=payload.export_type,
        file_path=file_path,
        created_by=principal.user_id,
    )
    repository.add_export(export)
    repository.add_audit_event(
        AuditEvent(
            organization_id=principal.organization_id,
            project_id=run.project_id,
            actor_id=principal.user_id,
            event_type="export.created",
            entity_type="export",
            entity_id=export.id,
            details={"export_type": export.export_type},
        )
    )
    return export


@router.get("/projects/{project_id}/audit-events", response_model=list[AuditEvent])
async def list_project_audit_events(
    project_id: str,
    principal: Principal = Depends(get_principal),
    repository: InMemoryRepository = Depends(get_repo),
) -> list[AuditEvent]:
    try:
        return repository.list_project_audit_events(project_id, principal.organization_id)
    except (NotFoundError, TenantAccessError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
