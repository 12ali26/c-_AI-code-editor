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


async def create_project_dataset_and_run(client, tmp_path, monkeypatch, project_name: str = "Read API Project"):
    monkeypatch.setenv("LOCAL_STORAGE_ROOT", str(tmp_path))
    project_response = await client.post("/api/v1/projects", json={"name": project_name})
    project = project_response.json()

    sample_path = Path(__file__).parents[1] / "samples" / "sample_triangle.csv"
    with sample_path.open("rb") as file:
        upload_response = await client.post(
            f"/api/v1/projects/{project['id']}/datasets",
            files={"file": ("sample_triangle.csv", file, "text/csv")},
        )
    dataset = upload_response.json()

    run_response = await client.post(
        f"/api/v1/datasets/{dataset['id']}/runs",
        json={"method": "chain_ladder"},
    )
    run = run_response.json()
    return project, dataset, run


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
async def test_read_endpoints_return_dashboard_foundation(client, tmp_path, monkeypatch) -> None:
    project, dataset, run = await create_project_dataset_and_run(client, tmp_path, monkeypatch)

    projects_response = await client.get("/api/v1/projects")
    assert projects_response.status_code == 200
    assert any(item["id"] == project["id"] for item in projects_response.json())

    project_response = await client.get(f"/api/v1/projects/{project['id']}")
    assert project_response.status_code == 200
    assert project_response.json()["id"] == project["id"]

    datasets_response = await client.get(f"/api/v1/projects/{project['id']}/datasets")
    assert datasets_response.status_code == 200
    assert [item["id"] for item in datasets_response.json()] == [dataset["id"]]

    runs_response = await client.get(f"/api/v1/projects/{project['id']}/runs")
    assert runs_response.status_code == 200
    assert [item["id"] for item in runs_response.json()] == [run["id"]]

    triangle_response = await client.get(f"/api/v1/datasets/{dataset['id']}/triangle")
    assert triangle_response.status_code == 200
    triangle = triangle_response.json()
    assert triangle["dataset_id"] == dataset["id"]
    assert triangle["triangle_basis"] == "cumulative"
    assert triangle["source_values"] == triangle["values"]
    assert triangle["origin_periods"] == ["2020", "2021", "2022", "2023", "2024"]


@pytest.mark.anyio
async def test_incremental_upload_is_normalized_before_model_run(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_STORAGE_ROOT", str(tmp_path))

    project_response = await client.post("/api/v1/projects", json={"name": "Incremental Upload"})
    project_id = project_response.json()["id"]
    incremental_csv = b"origin_period,12,24,36\n2022,100,50,25\n2023,120,60,\n"

    upload_response = await client.post(
        f"/api/v1/projects/{project_id}/datasets?triangle_basis=incremental",
        files={"file": ("incremental_triangle.csv", incremental_csv, "text/csv")},
    )
    assert upload_response.status_code == 200
    dataset = upload_response.json()
    assert dataset["triangle_basis"] == "incremental"

    run_response = await client.post(
        f"/api/v1/datasets/{dataset['id']}/runs",
        json={"method": "chain_ladder"},
    )
    assert run_response.status_code == 200
    run = run_response.json()
    assert run["result"]["latest_diagonal"] == [175, 180]
    assert run["result"]["incremental_triangle"][0] == [100, 50, 25]

    triangle_response = await client.get(f"/api/v1/datasets/{dataset['id']}/triangle")
    assert triangle_response.status_code == 200
    triangle = triangle_response.json()
    assert triangle["source_values"] == [[100, 50, 25], [120, 60, None]]
    assert triangle["values"] == [[100, 150, 175], [120, 180, None]]


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


@pytest.mark.anyio
async def test_read_endpoints_enforce_tenant_isolation(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_STORAGE_ROOT", str(tmp_path))
    project_response = await client.post(
        "/api/v1/projects",
        json={"name": "Tenant Read Project"},
        headers={"X-Org-Id": "tenant-read-a", "X-User-Id": "alice"},
    )
    project_id = project_response.json()["id"]

    sample_path = Path(__file__).parents[1] / "samples" / "sample_triangle.csv"
    with sample_path.open("rb") as file:
        upload_response = await client.post(
            f"/api/v1/projects/{project_id}/datasets",
            files={"file": ("sample_triangle.csv", file, "text/csv")},
            headers={"X-Org-Id": "tenant-read-a", "X-User-Id": "alice"},
        )
    dataset_id = upload_response.json()["id"]

    run_response = await client.post(
        f"/api/v1/datasets/{dataset_id}/runs",
        json={"method": "chain_ladder"},
        headers={"X-Org-Id": "tenant-read-a", "X-User-Id": "alice"},
    )
    assert run_response.status_code == 200

    other_headers = {"X-Org-Id": "tenant-read-b", "X-User-Id": "bob"}
    project_list_response = await client.get("/api/v1/projects", headers=other_headers)
    assert project_list_response.status_code == 200
    assert all(item["id"] != project_id for item in project_list_response.json())

    blocked_paths = [
        f"/api/v1/projects/{project_id}",
        f"/api/v1/projects/{project_id}/datasets",
        f"/api/v1/projects/{project_id}/runs",
        f"/api/v1/datasets/{dataset_id}/triangle",
    ]
    for path in blocked_paths:
        response = await client.get(path, headers=other_headers)
        assert response.status_code == 404
