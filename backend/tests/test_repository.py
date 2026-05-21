from sqlalchemy.orm import sessionmaker

from app.database import create_app_engine, init_db
from app.models import (
    AuditEvent,
    Dataset,
    ModelRun,
    Project,
    RunStatus,
    Triangle,
    TriangleValueType,
    ReservingResult,
)
from app.repository import DatabaseRepository


def test_database_repository_persists_core_entities_across_sessions(tmp_path) -> None:
    engine = create_app_engine(f"sqlite:///{tmp_path / 'repository.db'}")
    init_db(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    first_repo = DatabaseRepository(session_factory)
    first_repo.ensure_principal("org", "user")
    project = first_repo.add_project(Project(name="Persisted project", organization_id="org", created_by="user"))
    dataset = Dataset(
        organization_id="org",
        project_id=project.id,
        filename="triangle.csv",
        value_type=TriangleValueType.paid,
        origin_column="origin_period",
        development_columns=["12", "24"],
        raw_file_path="/tmp/triangle.csv",
        created_by="user",
    )
    triangle = Triangle(
        organization_id="org",
        dataset_id=dataset.id,
        origin_periods=["2023", "2024"],
        development_periods=["12", "24"],
        values=[[100, 150], [120, None]],
        source_values=[[100, 150], [120, None]],
    )
    first_repo.add_dataset(dataset, triangle)
    run = first_repo.add_run(
        ModelRun(
            organization_id="org",
            project_id=project.id,
            dataset_id=dataset.id,
            triangle_id=triangle.id,
            assumption_set_id="assump_1",
            method="chain_ladder",
            status=RunStatus.completed,
            result=ReservingResult(
                latest_diagonal=[150, 120],
                age_to_age_factors=[1.5],
                cumulative_development_factors=[1.5, 1],
                ultimate_by_origin=[150, 180],
                ibnr_by_origin=[0, 60],
                total_latest=270,
                total_ultimate=330,
                total_ibnr=60,
            ),
            created_by="user",
        )
    )
    first_repo.add_audit_event(
        AuditEvent(
            organization_id="org",
            project_id=project.id,
            actor_id="user",
            event_type="model_run.created",
            entity_type="model_run",
            entity_id=run.id,
        )
    )

    second_repo = DatabaseRepository(session_factory)

    assert second_repo.get_project(project.id, "org").name == "Persisted project"
    assert second_repo.get_dataset(dataset.id, "org").filename == "triangle.csv"
    assert second_repo.get_triangle_for_dataset(dataset.id, "org").values == [[100, 150], [120, None]]
    assert second_repo.get_run(run.id, "org").result.total_ibnr == 60
    assert len(second_repo.list_project_audit_events(project.id, "org")) == 1

    second_repo.delete_project(project.id, "org")

    assert second_repo.list_projects("org") == []
