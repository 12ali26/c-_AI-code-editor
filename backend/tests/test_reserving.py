from app.models import Triangle
from app.services.reserving import run_chain_ladder


def test_chain_ladder_calculates_ibnr_from_sample_triangle() -> None:
    triangle = Triangle(
        organization_id="org",
        dataset_id="data",
        origin_periods=["2020", "2021", "2022", "2023", "2024"],
        development_periods=["12", "24", "36", "48", "60"],
        values=[
            [1250, 1850, 2210, 2400, 2475],
            [1325, 1960, 2340, 2550, None],
            [1410, 2085, 2490, None, None],
            [1515, 2240, None, None, None],
            [1620, None, None, None, None],
        ],
    )

    result = run_chain_ladder(triangle)

    assert len(result.age_to_age_factors) == 4
    assert result.total_latest == 11375
    assert result.total_ultimate > result.total_latest
    assert result.total_ibnr > 0
    assert result.link_ratio_triangle[0] == [1.48, 1.194595, 1.085973, 1.03125]
    assert result.projected_cumulative_triangle[-1][-1] == result.ultimate_by_origin[-1]
    assert result.incremental_triangle[0] == [1250, 600, 360, 190, 75]
    assert result.factor_diagnostics[0]["observation_count"] == 4


def test_chain_ladder_allows_factor_overrides() -> None:
    triangle = Triangle(
        organization_id="org",
        dataset_id="data",
        origin_periods=["2023", "2024"],
        development_periods=["12", "24"],
        values=[[100, 150], [120, None]],
    )

    result = run_chain_ladder(triangle, selected_factors=[1.25])

    assert result.age_to_age_factors == [1.25]
    assert result.ultimate_by_origin == [150, 150]
    assert result.factor_diagnostics[0]["volume_weighted"] == 1.5
    assert result.factor_diagnostics[0]["selected"] == 1.25


def test_chain_ladder_rejects_invalid_factor_overrides() -> None:
    triangle = Triangle(
        organization_id="org",
        dataset_id="data",
        origin_periods=["2023", "2024"],
        development_periods=["12", "24"],
        values=[[100, 150], [120, None]],
    )

    try:
        run_chain_ladder(triangle, selected_factors=[0])
    except ValueError as error:
        assert "positive" in str(error)
    else:
        raise AssertionError("Expected invalid factor override to fail")
