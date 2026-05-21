from pathlib import Path

import httpx
import pytest

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client


@pytest.mark.anyio
async def test_project_upload_run_selection_export_and_audit_flow(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_STORAGE_ROOT", str(tmp_path))

    project_response = await client.post("/api/v1/projects", json={"name": "Q4 Reserving"})
    assert project_response.status_code == 200
    project_id = project_response.json()["id"]

    sample_path = Path(__file__).parents[1] / "samples" / "sample_triangle.csv"
    with sample_path.open("rb") as file:
        upload_response = await client.post(
            f"/api/v1/projects/{project_id}/datasets",
            files={"file": ("sample_triangle.csv", file, "text/csv")},
        )
    assert upload_response.status_code == 200
    dataset_id = upload_response.json()["id"]

    validation_response = await client.post(f"/api/v1/datasets/{dataset_id}/validate")
    assert validation_response.status_code == 200
    assert validation_response.json()["valid"] is True

    run_response = await client.post(f"/api/v1/datasets/{dataset_id}/runs", json={"method": "chain_ladder"})
    assert run_response.status_code == 200
    run = run_response.json()
    assert run["result"]["total_ibnr"] > 0

    selection_response = await client.post(
        f"/api/v1/runs/{run['id']}/selections",
        json={"reason": "Reserve committee selected default factors", "comment": "No override"},
    )
    assert selection_response.status_code == 200

    export_response = await client.post(f"/api/v1/runs/{run['id']}/exports", json={"export_type": "excel"})
    assert export_response.status_code == 200
    assert Path(export_response.json()["file_path"]).exists()

    audit_response = await client.get(f"/api/v1/projects/{project_id}/audit-events")
    assert audit_response.status_code == 200
    assert len(audit_response.json()) >= 4


@pytest.mark.anyio
async def test_tenant_isolation_blocks_cross_org_access(client) -> None:
    project_response = await client.post(
        "/api/v1/projects",
        json={"name": "Tenant A Project"},
        headers={"X-Org-Id": "tenant-a", "X-User-Id": "alice"},
    )
    project_id = project_response.json()["id"]

    response = await client.get(
        f"/api/v1/projects/{project_id}/audit-events",
        headers={"X-Org-Id": "tenant-b", "X-User-Id": "bob"},
    )

    assert response.status_code == 404
