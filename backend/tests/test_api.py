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

    run_response = await client.post(
        f"/api/v1/datasets/{dataset_id}/runs",
        json={
            "method": "chain_ladder",
            "selected_factors": [1.45, 1.18, 1.08, 1.03],
            "assumption_name": "Reserve committee selection",
        },
    )
    assert run_response.status_code == 200
    run = run_response.json()
    assert run["result"]["total_ibnr"] > 0
    assert run["result"]["age_to_age_factors"] == [1.45, 1.18, 1.08, 1.03]
    assert run["result"]["projected_cumulative_triangle"][-1][-1] > 0

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
async def test_bornhuetter_ferguson_run_flow(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_STORAGE_ROOT", str(tmp_path))

    project_response = await client.post("/api/v1/projects", json={"name": "BF Reserving"})
    project_id = project_response.json()["id"]

    sample_path = Path(__file__).parents[1] / "samples" / "sample_triangle.csv"
    with sample_path.open("rb") as file:
        upload_response = await client.post(
            f"/api/v1/projects/{project_id}/datasets",
            files={"file": ("sample_triangle.csv", file, "text/csv")},
        )
    dataset_id = upload_response.json()["id"]

    run_response = await client.post(
        f"/api/v1/datasets/{dataset_id}/runs",
        json={
            "method": "bornhuetter_ferguson",
            "assumption_name": "BF with selected ELR",
            "selected_factors": [1.45, 1.18, 1.08, 1.03],
            "exposure_values": [3500, 3700, 3900, 4200, 4500],
            "expected_loss_ratio": 0.72,
        },
    )

    assert run_response.status_code == 200
    run = run_response.json()
    assert run["method"] == "bornhuetter_ferguson"
    assert run["result"]["diagnostics"]["expected_loss_ratio"] == 0.72
    assert run["result"]["diagnostics"]["expected_ultimate_by_origin"] == [2520, 2664, 2808, 3024, 3240]


@pytest.mark.anyio
async def test_bornhuetter_ferguson_requires_assumptions(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_STORAGE_ROOT", str(tmp_path))

    project_response = await client.post("/api/v1/projects", json={"name": "BF Missing Inputs"})
    project_id = project_response.json()["id"]

    sample_path = Path(__file__).parents[1] / "samples" / "sample_triangle.csv"
    with sample_path.open("rb") as file:
        upload_response = await client.post(
            f"/api/v1/projects/{project_id}/datasets",
            files={"file": ("sample_triangle.csv", file, "text/csv")},
        )
    dataset_id = upload_response.json()["id"]

    run_response = await client.post(
        f"/api/v1/datasets/{dataset_id}/runs",
        json={"method": "bornhuetter_ferguson"},
    )

    assert run_response.status_code == 400
    assert "requires exposure_values" in run_response.json()["detail"]


@pytest.mark.anyio
async def test_cape_cod_run_and_export_flow(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_STORAGE_ROOT", str(tmp_path))

    project_response = await client.post("/api/v1/projects", json={"name": "Cape Cod Reserving"})
    project_id = project_response.json()["id"]

    sample_path = Path(__file__).parents[1] / "samples" / "sample_triangle.csv"
    with sample_path.open("rb") as file:
        upload_response = await client.post(
            f"/api/v1/projects/{project_id}/datasets",
            files={"file": ("sample_triangle.csv", file, "text/csv")},
        )
    dataset_id = upload_response.json()["id"]

    run_response = await client.post(
        f"/api/v1/datasets/{dataset_id}/runs",
        json={
            "method": "cape_cod",
            "assumption_name": "Cape Cod selected exposure",
            "selected_factors": [1.45, 1.18, 1.08, 1.03],
            "exposure_values": [3500, 3700, 3900, 4200, 4500],
        },
    )

    assert run_response.status_code == 200
    run = run_response.json()
    assert run["method"] == "cape_cod"
    assert run["result"]["diagnostics"]["cape_cod_apriori"] > 0
    assert run["result"]["diagnostics"]["percent_unreported_by_origin"][0] == 0

    export_response = await client.post(f"/api/v1/runs/{run['id']}/exports", json={"export_type": "excel"})
    assert export_response.status_code == 200
    assert Path(export_response.json()["file_path"]).exists()


@pytest.mark.anyio
async def test_cape_cod_requires_exposures(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_STORAGE_ROOT", str(tmp_path))

    project_response = await client.post("/api/v1/projects", json={"name": "Cape Cod Missing Inputs"})
    project_id = project_response.json()["id"]

    sample_path = Path(__file__).parents[1] / "samples" / "sample_triangle.csv"
    with sample_path.open("rb") as file:
        upload_response = await client.post(
            f"/api/v1/projects/{project_id}/datasets",
            files={"file": ("sample_triangle.csv", file, "text/csv")},
        )
    dataset_id = upload_response.json()["id"]

    missing_response = await client.post(
        f"/api/v1/datasets/{dataset_id}/runs",
        json={"method": "cape_cod"},
    )
    assert missing_response.status_code == 400
    assert "requires exposure_values" in missing_response.json()["detail"]

    mismatch_response = await client.post(
        f"/api/v1/datasets/{dataset_id}/runs",
        json={"method": "cape_cod", "exposure_values": [3500]},
    )
    assert mismatch_response.status_code == 400
    assert "Exposure value count" in mismatch_response.json()["detail"]


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
