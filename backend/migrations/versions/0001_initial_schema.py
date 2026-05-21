from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("review_status", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_projects_organization_id", "projects", ["organization_id"])
    op.create_table(
        "datasets",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", sa.String(length=80), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("value_type", sa.String(length=80), nullable=False),
        sa.Column("triangle_basis", sa.String(length=80), nullable=False),
        sa.Column("origin_column", sa.String(length=255), nullable=False),
        sa.Column("development_columns", sa.JSON(), nullable=False),
        sa.Column("raw_file_path", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_datasets_organization_id", "datasets", ["organization_id"])
    op.create_index("ix_datasets_project_id", "datasets", ["project_id"])
    op.create_table(
        "triangles",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("dataset_id", sa.String(length=80), sa.ForeignKey("datasets.id"), nullable=False, unique=True),
        sa.Column("origin_periods", sa.JSON(), nullable=False),
        sa.Column("development_periods", sa.JSON(), nullable=False),
        sa.Column("values", sa.JSON(), nullable=False),
        sa.Column("source_values", sa.JSON(), nullable=False),
        sa.Column("triangle_basis", sa.String(length=80), nullable=False),
        sa.Column("is_cumulative", sa.Boolean(), nullable=False),
        sa.Column("validation_warnings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_triangles_organization_id", "triangles", ["organization_id"])
    op.create_index("ix_triangles_dataset_id", "triangles", ["dataset_id"])
    op.create_table(
        "assumption_sets",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("dataset_id", sa.String(length=80), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("method", sa.String(length=80), nullable=False),
        sa.Column("selected_factors", sa.JSON(), nullable=True),
        sa.Column("exposure_values", sa.JSON(), nullable=True),
        sa.Column("expected_loss_ratio", sa.JSON(), nullable=True),
        sa.Column("trend", sa.JSON(), nullable=False),
        sa.Column("decay", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assumption_sets_organization_id", "assumption_sets", ["organization_id"])
    op.create_index("ix_assumption_sets_dataset_id", "assumption_sets", ["dataset_id"])
    op.create_table(
        "model_runs",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", sa.String(length=80), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("dataset_id", sa.String(length=80), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("triangle_id", sa.String(length=80), sa.ForeignKey("triangles.id"), nullable=False),
        sa.Column("assumption_set_id", sa.String(length=80), nullable=False),
        sa.Column("method", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_model_runs_organization_id", "model_runs", ["organization_id"])
    op.create_index("ix_model_runs_project_id", "model_runs", ["project_id"])
    op.create_index("ix_model_runs_dataset_id", "model_runs", ["dataset_id"])
    op.create_table(
        "selections",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("run_id", sa.String(length=80), sa.ForeignKey("model_runs.id"), nullable=False),
        sa.Column("selected_factors", sa.JSON(), nullable=True),
        sa.Column("selected_ultimates", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_selections_organization_id", "selections", ["organization_id"])
    op.create_index("ix_selections_run_id", "selections", ["run_id"])
    op.create_table(
        "export_jobs",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("run_id", sa.String(length=80), sa.ForeignKey("model_runs.id"), nullable=False),
        sa.Column("export_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_export_jobs_organization_id", "export_jobs", ["organization_id"])
    op.create_index("ix_export_jobs_run_id", "export_jobs", ["run_id"])
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", sa.String(length=80), nullable=True),
        sa.Column("actor_id", sa.String(length=80), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=120), nullable=False),
        sa.Column("entity_id", sa.String(length=80), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_organization_id", "audit_events", ["organization_id"])
    op.create_index("ix_audit_events_project_id", "audit_events", ["project_id"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("export_jobs")
    op.drop_table("selections")
    op.drop_table("model_runs")
    op.drop_table("assumption_sets")
    op.drop_table("triangles")
    op.drop_table("datasets")
    op.drop_table("projects")
    op.drop_table("users")
    op.drop_table("organizations")

