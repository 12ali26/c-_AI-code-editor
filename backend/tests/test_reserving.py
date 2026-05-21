from app.models import Triangle
from app.services.reserving import run_bornhuetter_ferguson, run_chain_ladder


def sample_triangle() -> Triangle:
    return Triangle(
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


def test_chain_ladder_calculates_ibnr_from_sample_triangle() -> None:
    triangle = sample_triangle()

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


def test_bornhuetter_ferguson_uses_expected_loss_and_unreported_percentage() -> None:
    result = run_bornhuetter_ferguson(
        sample_triangle(),
        exposure_values=[3500, 3700, 3900, 4200, 4500],
        expected_loss_ratio=0.72,
        selected_factors=[1.45, 1.18, 1.08, 1.03],
    )

    assert result.diagnostics["method"] == "bornhuetter_ferguson"
    assert result.age_to_age_factors == [1.45, 1.18, 1.08, 1.03]
    assert result.diagnostics["expected_ultimate_by_origin"] == [2520, 2664, 2808, 3024, 3240]
    assert result.diagnostics["percent_unreported_by_origin"][0] == 0
    assert result.ibnr_by_origin[0] == 0
    assert result.ultimate_by_origin[-1] > result.latest_diagonal[-1]
    assert result.total_ibnr == round(sum(result.ibnr_by_origin), 2)


def test_bornhuetter_ferguson_requires_exposure_for_each_origin() -> None:
    try:
        run_bornhuetter_ferguson(
            sample_triangle(),
            exposure_values=[3500],
            expected_loss_ratio=0.72,
        )
    except ValueError as error:
        assert "Exposure value count" in str(error)
    else:
        raise AssertionError("Expected mismatched exposure values to fail")
