from __future__ import annotations

from collections import defaultdict
from typing import TypeVar

from app.models import (
    AuditEvent,
    Dataset,
    ExportJob,
    ModelRun,
    Organization,
    Project,
    Selection,
    Triangle,
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

    def get_project(self, project_id: str, organization_id: str) -> Project:
        return self._get_for_org(self.projects, project_id, organization_id)

    def get_dataset(self, dataset_id: str, organization_id: str) -> Dataset:
        return self._get_for_org(self.datasets, dataset_id, organization_id)

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

    def _get_for_org(self, store: dict[str, T], entity_id: str, organization_id: str) -> T:
        entity = store.get(entity_id)
        if entity is None:
            raise NotFoundError(f"{entity_id} was not found")
        entity_org = getattr(entity, "organization_id", None)
        if entity_org != organization_id:
            raise TenantAccessError(f"{entity_id} does not belong to organization {organization_id}")
        return entity


repo = InMemoryRepository()

