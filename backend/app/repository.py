from __future__ import annotations

from collections import defaultdict
from typing import Callable, TypeVar

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db_models import (
    AssumptionSetRow,
    AuditEventRow,
    DatasetRow,
    ExportJobRow,
    ModelRunRow,
    OrganizationRow,
    ProjectRow,
    SelectionRow,
    TriangleRow,
    UserRow,
)
from app.models import (
    AssumptionSet,
    AuditEvent,
    Dataset,
    ExportJob,
    ModelRun,
    Organization,
    Project,
    ReservingResult,
    ReviewStatus,
    RunStatus,
    Selection,
    Triangle,
    TriangleBasis,
    TriangleValueType,
    User,
)

T = TypeVar("T")


class NotFoundError(Exception):
    pass


class TenantAccessError(Exception):
    pass


class InMemoryRepository:
    """Development repository. Replace with SQLAlchemy-backed repositories for production."""

    def __init__(self) -> None:
        self.organizations: dict[str, Organization] = {}
        self.users: dict[str, User] = {}
        self.projects: dict[str, Project] = {}
        self.assumption_sets: dict[str, AssumptionSet] = {}
        self.datasets: dict[str, Dataset] = {}
        self.triangles: dict[str, Triangle] = {}
        self.model_runs: dict[str, ModelRun] = {}
        self.selections: dict[str, Selection] = {}
        self.exports: dict[str, ExportJob] = {}
        self.audit_events: dict[str, AuditEvent] = {}
        self.dataset_triangles: dict[str, str] = {}
        self.project_datasets: dict[str, list[str]] = defaultdict(list)
        self.run_selections: dict[str, list[str]] = defaultdict(list)

    def ensure_principal(self, organization_id: str, user_id: str) -> None:
        if organization_id not in self.organizations:
            self.organizations[organization_id] = Organization(id=organization_id, name="Demo Actuarial Team")
        if user_id not in self.users:
            self.users[user_id] = User(
                id=user_id,
                organization_id=organization_id,
                email=f"{user_id}@example.com",
                name="Demo Actuary",
            )

    def add_project(self, project: Project) -> Project:
        self.projects[project.id] = project
        return project

    def add_dataset(self, dataset: Dataset, triangle: Triangle) -> tuple[Dataset, Triangle]:
        self.datasets[dataset.id] = dataset
        self.triangles[triangle.id] = triangle
        self.dataset_triangles[dataset.id] = triangle.id
        self.project_datasets[dataset.project_id].append(dataset.id)
        return dataset, triangle

    def add_run(self, run: ModelRun) -> ModelRun:
        self.model_runs[run.id] = run
        return run

    def add_assumption(self, assumption: AssumptionSet) -> AssumptionSet:
        self.assumption_sets[assumption.id] = assumption
        return assumption

    def add_selection(self, selection: Selection) -> Selection:
        self.selections[selection.id] = selection
        self.run_selections[selection.run_id].append(selection.id)
        return selection

    def add_export(self, export: ExportJob) -> ExportJob:
        self.exports[export.id] = export
        return export

    def add_audit_event(self, event: AuditEvent) -> AuditEvent:
        self.audit_events[event.id] = event
        return event

    def list_projects(self, organization_id: str) -> list[Project]:
        return sorted(
            [project for project in self.projects.values() if project.organization_id == organization_id],
            key=lambda project: project.created_at,
            reverse=True,
        )

    def get_project(self, project_id: str, organization_id: str) -> Project:
        return self._get_for_org(self.projects, project_id, organization_id)

    def get_dataset(self, dataset_id: str, organization_id: str) -> Dataset:
        return self._get_for_org(self.datasets, dataset_id, organization_id)

    def list_project_datasets(self, project_id: str, organization_id: str) -> list[Dataset]:
        self.get_project(project_id, organization_id)
        return [
            self.datasets[dataset_id]
            for dataset_id in self.project_datasets.get(project_id, [])
            if self.datasets[dataset_id].organization_id == organization_id
        ]

    def get_triangle_for_dataset(self, dataset_id: str, organization_id: str) -> Triangle:
        triangle_id = self.dataset_triangles.get(dataset_id)
        if not triangle_id:
            raise NotFoundError(f"Triangle for dataset {dataset_id} was not found")
        return self._get_for_org(self.triangles, triangle_id, organization_id)

    def get_run(self, run_id: str, organization_id: str) -> ModelRun:
        return self._get_for_org(self.model_runs, run_id, organization_id)

    def list_project_runs(self, project_id: str, organization_id: str) -> list[ModelRun]:
        self.get_project(project_id, organization_id)
        return [
            run
            for run in self.model_runs.values()
            if run.project_id == project_id and run.organization_id == organization_id
        ]

    def list_project_audit_events(self, project_id: str, organization_id: str) -> list[AuditEvent]:
        self.get_project(project_id, organization_id)
        return sorted(
            [
                event
                for event in self.audit_events.values()
                if event.project_id == project_id and event.organization_id == organization_id
            ],
            key=lambda event: event.created_at,
            reverse=True,
        )

    def delete_project(self, project_id: str, organization_id: str) -> None:
        self.get_project(project_id, organization_id)
        dataset_ids = list(self.project_datasets.get(project_id, []))
        run_ids = [
            run_id
            for run_id, run in self.model_runs.items()
            if run.project_id == project_id and run.organization_id == organization_id
        ]
        for run_id in run_ids:
            self.model_runs.pop(run_id, None)
            self.run_selections.pop(run_id, None)
        for selection_id, selection in list(self.selections.items()):
            if selection.run_id in run_ids and selection.organization_id == organization_id:
                self.selections.pop(selection_id, None)
        for export_id, export in list(self.exports.items()):
            if export.run_id in run_ids and export.organization_id == organization_id:
                self.exports.pop(export_id, None)
        for dataset_id in dataset_ids:
            self.datasets.pop(dataset_id, None)
            triangle_id = self.dataset_triangles.pop(dataset_id, None)
            if triangle_id:
                self.triangles.pop(triangle_id, None)
        for assumption_id, assumption in list(self.assumption_sets.items()):
            if assumption.dataset_id in dataset_ids and assumption.organization_id == organization_id:
                self.assumption_sets.pop(assumption_id, None)
        for event_id, event in list(self.audit_events.items()):
            if event.project_id == project_id and event.organization_id == organization_id:
                self.audit_events.pop(event_id, None)
        self.project_datasets.pop(project_id, None)
        self.projects.pop(project_id, None)

    def _get_for_org(self, store: dict[str, T], entity_id: str, organization_id: str) -> T:
        entity = store.get(entity_id)
        if entity is None:
            raise NotFoundError(f"{entity_id} was not found")
        entity_org = getattr(entity, "organization_id", None)
        if entity_org != organization_id:
            raise TenantAccessError(f"{entity_id} does not belong to organization {organization_id}")
        return entity


class DatabaseRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self.session_factory = session_factory

    def ensure_principal(self, organization_id: str, user_id: str) -> None:
        with self.session_factory() as session:
            if session.get(OrganizationRow, organization_id) is None:
                organization = Organization(id=organization_id, name="Demo Actuarial Team")
                session.add(_organization_to_row(organization))
            if session.get(UserRow, user_id) is None:
                user = User(
                    id=user_id,
                    organization_id=organization_id,
                    email=f"{user_id}@example.com",
                    name="Demo Actuary",
                )
                session.add(_user_to_row(user))
            session.commit()

    def add_project(self, project: Project) -> Project:
        with self.session_factory() as session:
            session.merge(_project_to_row(project))
            session.commit()
        return project

    def add_dataset(self, dataset: Dataset, triangle: Triangle) -> tuple[Dataset, Triangle]:
        with self.session_factory() as session:
            session.merge(_dataset_to_row(dataset))
            session.merge(_triangle_to_row(triangle))
            session.commit()
        return dataset, triangle

    def add_assumption(self, assumption: AssumptionSet) -> AssumptionSet:
        with self.session_factory() as session:
            session.merge(_assumption_to_row(assumption))
            session.commit()
        return assumption

    def add_run(self, run: ModelRun) -> ModelRun:
        with self.session_factory() as session:
            session.merge(_run_to_row(run))
            session.commit()
        return run

    def add_selection(self, selection: Selection) -> Selection:
        with self.session_factory() as session:
            session.merge(_selection_to_row(selection))
            session.commit()
        return selection

    def add_export(self, export: ExportJob) -> ExportJob:
        with self.session_factory() as session:
            session.merge(_export_to_row(export))
            session.commit()
        return export

    def add_audit_event(self, event: AuditEvent) -> AuditEvent:
        with self.session_factory() as session:
            session.merge(_audit_to_row(event))
            session.commit()
        return event

    def list_projects(self, organization_id: str) -> list[Project]:
        with self.session_factory() as session:
            rows = session.scalars(
                select(ProjectRow)
                .where(ProjectRow.organization_id == organization_id)
                .order_by(ProjectRow.created_at.desc())
            ).all()
            return [_row_to_project(row) for row in rows]

    def get_project(self, project_id: str, organization_id: str) -> Project:
        with self.session_factory() as session:
            return _row_to_project(self._get_for_org(session, ProjectRow, project_id, organization_id))

    def get_dataset(self, dataset_id: str, organization_id: str) -> Dataset:
        with self.session_factory() as session:
            return _row_to_dataset(self._get_for_org(session, DatasetRow, dataset_id, organization_id))

    def list_project_datasets(self, project_id: str, organization_id: str) -> list[Dataset]:
        with self.session_factory() as session:
            self._get_for_org(session, ProjectRow, project_id, organization_id)
            rows = session.scalars(
                select(DatasetRow)
                .where(DatasetRow.project_id == project_id, DatasetRow.organization_id == organization_id)
                .order_by(DatasetRow.created_at.asc())
            ).all()
            return [_row_to_dataset(row) for row in rows]

    def get_triangle_for_dataset(self, dataset_id: str, organization_id: str) -> Triangle:
        with self.session_factory() as session:
            self._get_for_org(session, DatasetRow, dataset_id, organization_id)
            row = session.scalar(
                select(TriangleRow).where(
                    TriangleRow.dataset_id == dataset_id,
                    TriangleRow.organization_id == organization_id,
                )
            )
            if row is None:
                raise NotFoundError(f"Triangle for dataset {dataset_id} was not found")
            return _row_to_triangle(row)

    def get_run(self, run_id: str, organization_id: str) -> ModelRun:
        with self.session_factory() as session:
            return _row_to_run(self._get_for_org(session, ModelRunRow, run_id, organization_id))

    def list_project_runs(self, project_id: str, organization_id: str) -> list[ModelRun]:
        with self.session_factory() as session:
            self._get_for_org(session, ProjectRow, project_id, organization_id)
            rows = session.scalars(
                select(ModelRunRow)
                .where(ModelRunRow.project_id == project_id, ModelRunRow.organization_id == organization_id)
                .order_by(ModelRunRow.created_at.asc())
            ).all()
            return [_row_to_run(row) for row in rows]

    def list_project_audit_events(self, project_id: str, organization_id: str) -> list[AuditEvent]:
        with self.session_factory() as session:
            self._get_for_org(session, ProjectRow, project_id, organization_id)
            rows = session.scalars(
                select(AuditEventRow)
                .where(AuditEventRow.project_id == project_id, AuditEventRow.organization_id == organization_id)
                .order_by(AuditEventRow.created_at.desc())
            ).all()
            return [_row_to_audit(row) for row in rows]

    def delete_project(self, project_id: str, organization_id: str) -> None:
        with self.session_factory() as session:
            self._get_for_org(session, ProjectRow, project_id, organization_id)
            dataset_ids = session.scalars(
                select(DatasetRow.id).where(
                    DatasetRow.project_id == project_id,
                    DatasetRow.organization_id == organization_id,
                )
            ).all()
            run_ids = session.scalars(
                select(ModelRunRow.id).where(
                    ModelRunRow.project_id == project_id,
                    ModelRunRow.organization_id == organization_id,
                )
            ).all()

            if run_ids:
                session.execute(delete(SelectionRow).where(SelectionRow.run_id.in_(run_ids)))
                session.execute(delete(ExportJobRow).where(ExportJobRow.run_id.in_(run_ids)))
                session.execute(delete(ModelRunRow).where(ModelRunRow.id.in_(run_ids)))
            if dataset_ids:
                session.execute(delete(AssumptionSetRow).where(AssumptionSetRow.dataset_id.in_(dataset_ids)))
                session.execute(delete(TriangleRow).where(TriangleRow.dataset_id.in_(dataset_ids)))
                session.execute(delete(DatasetRow).where(DatasetRow.id.in_(dataset_ids)))
            session.execute(
                delete(AuditEventRow).where(
                    AuditEventRow.project_id == project_id,
                    AuditEventRow.organization_id == organization_id,
                )
            )
            session.execute(
                delete(ProjectRow).where(
                    ProjectRow.id == project_id,
                    ProjectRow.organization_id == organization_id,
                )
            )
            session.commit()

    def _get_for_org(self, session: Session, row_type: type[T], entity_id: str, organization_id: str) -> T:
        row = session.get(row_type, entity_id)
        if row is None:
            raise NotFoundError(f"{entity_id} was not found")
        if getattr(row, "organization_id", None) != organization_id:
            raise TenantAccessError(f"{entity_id} does not belong to organization {organization_id}")
        return row


def _organization_to_row(organization: Organization) -> OrganizationRow:
    return OrganizationRow(**organization.model_dump())


def _row_to_project(row: ProjectRow) -> Project:
    return Project(
        id=row.id,
        organization_id=row.organization_id,
        name=row.name,
        description=row.description,
        created_by=row.created_by,
        review_status=ReviewStatus(row.review_status),
        created_at=row.created_at,
    )


def _project_to_row(project: Project) -> ProjectRow:
    return ProjectRow(
        id=project.id,
        organization_id=project.organization_id,
        name=project.name,
        description=project.description,
        created_by=project.created_by,
        review_status=project.review_status.value,
        created_at=project.created_at,
    )


def _user_to_row(user: User) -> UserRow:
    return UserRow(**user.model_dump())


def _row_to_dataset(row: DatasetRow) -> Dataset:
    return Dataset(
        id=row.id,
        organization_id=row.organization_id,
        project_id=row.project_id,
        filename=row.filename,
        value_type=TriangleValueType(row.value_type),
        triangle_basis=TriangleBasis(row.triangle_basis),
        origin_column=row.origin_column,
        development_columns=row.development_columns,
        raw_file_path=row.raw_file_path,
        created_by=row.created_by,
        created_at=row.created_at,
    )


def _dataset_to_row(dataset: Dataset) -> DatasetRow:
    return DatasetRow(
        id=dataset.id,
        organization_id=dataset.organization_id,
        project_id=dataset.project_id,
        filename=dataset.filename,
        value_type=dataset.value_type.value,
        triangle_basis=dataset.triangle_basis.value,
        origin_column=dataset.origin_column,
        development_columns=dataset.development_columns,
        raw_file_path=dataset.raw_file_path,
        created_by=dataset.created_by,
        created_at=dataset.created_at,
    )


def _row_to_triangle(row: TriangleRow) -> Triangle:
    return Triangle(
        id=row.id,
        organization_id=row.organization_id,
        dataset_id=row.dataset_id,
        origin_periods=row.origin_periods,
        development_periods=row.development_periods,
        values=row.values,
        source_values=row.source_values,
        triangle_basis=TriangleBasis(row.triangle_basis),
        is_cumulative=row.is_cumulative,
        validation_warnings=row.validation_warnings,
        created_at=row.created_at,
    )


def _triangle_to_row(triangle: Triangle) -> TriangleRow:
    return TriangleRow(
        id=triangle.id,
        organization_id=triangle.organization_id,
        dataset_id=triangle.dataset_id,
        origin_periods=triangle.origin_periods,
        development_periods=triangle.development_periods,
        values=triangle.values,
        source_values=triangle.source_values,
        triangle_basis=triangle.triangle_basis.value,
        is_cumulative=triangle.is_cumulative,
        validation_warnings=triangle.validation_warnings,
        created_at=triangle.created_at,
    )


def _assumption_to_row(assumption: AssumptionSet) -> AssumptionSetRow:
    return AssumptionSetRow(
        id=assumption.id,
        organization_id=assumption.organization_id,
        dataset_id=assumption.dataset_id,
        name=assumption.name,
        method=assumption.method,
        selected_factors=assumption.selected_factors,
        exposure_values=assumption.exposure_values,
        expected_loss_ratio=assumption.expected_loss_ratio,
        trend=assumption.trend,
        decay=assumption.decay,
        created_by=assumption.created_by,
        created_at=assumption.created_at,
    )


def _row_to_run(row: ModelRunRow) -> ModelRun:
    return ModelRun(
        id=row.id,
        organization_id=row.organization_id,
        project_id=row.project_id,
        dataset_id=row.dataset_id,
        triangle_id=row.triangle_id,
        assumption_set_id=row.assumption_set_id,
        method=row.method,
        status=RunStatus(row.status),
        result=ReservingResult(**row.result),
        created_by=row.created_by,
        created_at=row.created_at,
    )


def _run_to_row(run: ModelRun) -> ModelRunRow:
    return ModelRunRow(
        id=run.id,
        organization_id=run.organization_id,
        project_id=run.project_id,
        dataset_id=run.dataset_id,
        triangle_id=run.triangle_id,
        assumption_set_id=run.assumption_set_id,
        method=run.method,
        status=run.status.value,
        result=run.result.model_dump(mode="json"),
        created_by=run.created_by,
        created_at=run.created_at,
    )


def _selection_to_row(selection: Selection) -> SelectionRow:
    return SelectionRow(
        id=selection.id,
        organization_id=selection.organization_id,
        run_id=selection.run_id,
        selected_factors=selection.selected_factors,
        selected_ultimates=selection.selected_ultimates,
        reason=selection.reason,
        comment=selection.comment,
        created_by=selection.created_by,
        created_at=selection.created_at,
    )


def _export_to_row(export: ExportJob) -> ExportJobRow:
    return ExportJobRow(
        id=export.id,
        organization_id=export.organization_id,
        run_id=export.run_id,
        export_type=export.export_type.value,
        status=export.status,
        file_path=export.file_path,
        created_by=export.created_by,
        created_at=export.created_at,
    )


def _audit_to_row(event: AuditEvent) -> AuditEventRow:
    return AuditEventRow(
        id=event.id,
        organization_id=event.organization_id,
        project_id=event.project_id,
        actor_id=event.actor_id,
        event_type=event.event_type,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        details=event.model_dump(mode="json")["details"],
        created_at=event.created_at,
    )


def _row_to_audit(row: AuditEventRow) -> AuditEvent:
    return AuditEvent(
        id=row.id,
        organization_id=row.organization_id,
        project_id=row.project_id,
        actor_id=row.actor_id,
        event_type=row.event_type,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        details=row.details,
        created_at=row.created_at,
    )


from app.database import SessionLocal, init_db  # noqa: E402

init_db()
repo = DatabaseRepository(SessionLocal)
