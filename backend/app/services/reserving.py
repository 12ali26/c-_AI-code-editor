from __future__ import annotations

from app.models import ReservingResult, Triangle


class ReservingError(ValueError):
    pass


def run_chain_ladder(triangle: Triangle, selected_factors: list[float] | None = None) -> ReservingResult:
    values = triangle.values
    if not values or not triangle.development_periods:
        raise ReservingError("Triangle has no values")
    _validate_rectangular_triangle(values)

    indicated_factors = _volume_weighted_age_to_age(values)
    if selected_factors is not None:
        _validate_selected_factors(selected_factors, len(triangle.development_periods) - 1)
    factors = selected_factors or indicated_factors
    if len(factors) != len(triangle.development_periods) - 1:
        raise ReservingError("Selected factor count must equal development period count minus one")

    cdfs = _cumulative_development_factors(factors)
    link_ratio_triangle = _link_ratio_triangle(values)
    projected_cumulative_triangle = _project_cumulative_triangle(values, factors)
    incremental_triangle = _incremental_triangle(projected_cumulative_triangle)
    latest = [_latest_observed(row) for row in values]
    latest_indexes = [_latest_observed_index(row) for row in values]
    ultimates: list[float] = []
    ibnr: list[float] = []

    for latest_value, latest_index in zip(latest, latest_indexes, strict=True):
        cdf = cdfs[latest_index] if latest_index is not None else 1.0
        ultimate = round(latest_value * cdf, 2)
        ultimates.append(ultimate)
        ibnr.append(round(ultimate - latest_value, 2))

    diagnostics = {
        "method": "chain_ladder",
        "factor_basis": "selected" if selected_factors is not None else "volume_weighted",
        "development_periods": triangle.development_periods,
        "origin_periods": triangle.origin_periods,
        "latest_observed_development_index": latest_indexes,
        "fully_developed_origin_count": sum(1 for index in latest_indexes if index == len(triangle.development_periods) - 1),
    }

    total_latest = round(sum(latest), 2)
    total_ultimate = round(sum(ultimates), 2)
    return ReservingResult(
        latest_diagonal=[round(value, 2) for value in latest],
        age_to_age_factors=[round(factor, 6) for factor in factors],
        cumulative_development_factors=[round(cdf, 6) for cdf in cdfs],
        link_ratio_triangle=_round_optional_matrix(link_ratio_triangle, 6),
        projected_cumulative_triangle=_round_optional_matrix(projected_cumulative_triangle, 2),
        incremental_triangle=_round_optional_matrix(incremental_triangle, 2),
        factor_diagnostics=_factor_diagnostics(values, indicated_factors, factors),
        ultimate_by_origin=ultimates,
        ibnr_by_origin=ibnr,
        total_latest=total_latest,
        total_ultimate=total_ultimate,
        total_ibnr=round(total_ultimate - total_latest, 2),
        diagnostics=diagnostics,
    )


def run_bornhuetter_ferguson(
    triangle: Triangle,
    exposure_values: list[float],
    expected_loss_ratio: float,
    selected_factors: list[float] | None = None,
) -> ReservingResult:
    values = triangle.values
    if not values or not triangle.development_periods:
        raise ReservingError("Triangle has no values")
    _validate_rectangular_triangle(values)
    _validate_exposure_values(exposure_values, len(triangle.origin_periods))
    if expected_loss_ratio < 0:
        raise ReservingError("Expected loss ratio must be non-negative")

    indicated_factors = _volume_weighted_age_to_age(values)
    if selected_factors is not None:
        _validate_selected_factors(selected_factors, len(triangle.development_periods) - 1)
    factors = selected_factors or indicated_factors

    cdfs = _cumulative_development_factors(factors)
    link_ratio_triangle = _link_ratio_triangle(values)
    projected_cumulative_triangle = _project_cumulative_triangle(values, factors)
    incremental_triangle = _incremental_triangle(projected_cumulative_triangle)
    latest = [_latest_observed(row) for row in values]
    latest_indexes = [_latest_observed_index(row) for row in values]
    expected_ultimates = [exposure * expected_loss_ratio for exposure in exposure_values]

    ultimates: list[float] = []
    ibnr: list[float] = []
    percent_reported: list[float] = []
    percent_unreported: list[float] = []

    for latest_value, latest_index, expected_ultimate in zip(
        latest,
        latest_indexes,
        expected_ultimates,
        strict=True,
    ):
        cdf = cdfs[latest_index] if latest_index is not None else 1.0
        reported = 1 / cdf if cdf > 0 else 1.0
        unreported = max(0.0, 1 - reported)
        bf_ibnr = expected_ultimate * unreported
        ibnr.append(round(bf_ibnr, 2))
        ultimates.append(round(latest_value + bf_ibnr, 2))
        percent_reported.append(round(reported, 6))
        percent_unreported.append(round(unreported, 6))

    total_latest = round(sum(latest), 2)
    total_ultimate = round(sum(ultimates), 2)
    diagnostics = {
        "method": "bornhuetter_ferguson",
        "factor_basis": "selected" if selected_factors is not None else "volume_weighted",
        "development_periods": triangle.development_periods,
        "origin_periods": triangle.origin_periods,
        "latest_observed_development_index": latest_indexes,
        "exposure_values": [round(value, 2) for value in exposure_values],
        "expected_loss_ratio": expected_loss_ratio,
        "expected_ultimate_by_origin": [round(value, 2) for value in expected_ultimates],
        "percent_reported_by_origin": percent_reported,
        "percent_unreported_by_origin": percent_unreported,
    }

    return ReservingResult(
        latest_diagonal=[round(value, 2) for value in latest],
        age_to_age_factors=[round(factor, 6) for factor in factors],
        cumulative_development_factors=[round(cdf, 6) for cdf in cdfs],
        link_ratio_triangle=_round_optional_matrix(link_ratio_triangle, 6),
        projected_cumulative_triangle=_round_optional_matrix(projected_cumulative_triangle, 2),
        incremental_triangle=_round_optional_matrix(incremental_triangle, 2),
        factor_diagnostics=_factor_diagnostics(values, indicated_factors, factors),
        ultimate_by_origin=ultimates,
        ibnr_by_origin=ibnr,
        total_latest=total_latest,
        total_ultimate=total_ultimate,
        total_ibnr=round(total_ultimate - total_latest, 2),
        diagnostics=diagnostics,
    )


def _validate_rectangular_triangle(values: list[list[float | None]]) -> None:
    period_count = len(values[0])
    if period_count == 0:
        raise ReservingError("Triangle must contain at least one development period")
    if any(len(row) != period_count for row in values):
        raise ReservingError("Triangle rows must all have the same number of development periods")


def _validate_selected_factors(selected_factors: list[float], expected_count: int) -> None:
    if len(selected_factors) != expected_count:
        raise ReservingError("Selected factor count must equal development period count minus one")
    invalid = [factor for factor in selected_factors if factor <= 0]
    if invalid:
        raise ReservingError("Selected factors must be positive")


def _validate_exposure_values(exposure_values: list[float], expected_count: int) -> None:
    if len(exposure_values) != expected_count:
        raise ReservingError("Exposure value count must equal origin period count")
    if any(value < 0 for value in exposure_values):
        raise ReservingError("Exposure values must be non-negative")


def _volume_weighted_age_to_age(values: list[list[float | None]]) -> list[float]:
    factors: list[float] = []
    period_count = len(values[0])

    for column_index in range(period_count - 1):
        numerator = 0.0
        denominator = 0.0
        for row in values:
            current_value = row[column_index]
            next_value = row[column_index + 1]
            if current_value is None or next_value is None:
                continue
            if current_value <= 0:
                continue
            denominator += current_value
            numerator += next_value
        if denominator == 0:
            factors.append(1.0)
        else:
            factors.append(numerator / denominator)
    return factors


def _link_ratio_triangle(values: list[list[float | None]]) -> list[list[float | None]]:
    ratios: list[list[float | None]] = []
    period_count = len(values[0])
    for row in values:
        ratio_row: list[float | None] = []
        for column_index in range(period_count - 1):
            current_value = row[column_index]
            next_value = row[column_index + 1]
            if current_value is None or next_value is None or current_value <= 0:
                ratio_row.append(None)
            else:
                ratio_row.append(next_value / current_value)
        ratios.append(ratio_row)
    return ratios


def _project_cumulative_triangle(
    values: list[list[float | None]],
    selected_factors: list[float],
) -> list[list[float | None]]:
    projected: list[list[float | None]] = []
    for source_row in values:
        row = [value for value in source_row]
        latest_index = _latest_observed_index(row)
        if latest_index is not None:
            for column_index in range(latest_index + 1, len(row)):
                previous_value = row[column_index - 1]
                row[column_index] = None if previous_value is None else previous_value * selected_factors[column_index - 1]
        projected.append(row)
    return projected


def _incremental_triangle(cumulative_values: list[list[float | None]]) -> list[list[float | None]]:
    incremental: list[list[float | None]] = []
    for row in cumulative_values:
        incremental_row: list[float | None] = []
        previous_value = 0.0
        for value in row:
            if value is None:
                incremental_row.append(None)
                continue
            incremental_row.append(value - previous_value)
            previous_value = value
        incremental.append(incremental_row)
    return incremental


def _factor_diagnostics(
    values: list[list[float | None]],
    indicated_factors: list[float],
    selected_factors: list[float],
) -> list[dict[str, float | int]]:
    diagnostics: list[dict[str, float | int]] = []
    for column_index, indicated_factor in enumerate(indicated_factors):
        paired_values = [
            (row[column_index], row[column_index + 1])
            for row in values
            if row[column_index] is not None and row[column_index + 1] is not None and row[column_index] > 0
        ]
        link_ratios = [next_value / current_value for current_value, next_value in paired_values]
        diagnostics.append(
            {
                "development_index": column_index,
                "from_development_index": column_index,
                "to_development_index": column_index + 1,
                "observation_count": len(link_ratios),
                "volume_weighted": round(indicated_factor, 6),
                "simple_average": round(sum(link_ratios) / len(link_ratios), 6) if link_ratios else 1.0,
                "minimum": round(min(link_ratios), 6) if link_ratios else 1.0,
                "maximum": round(max(link_ratios), 6) if link_ratios else 1.0,
                "selected": round(selected_factors[column_index], 6),
            }
        )
    return diagnostics


def _cumulative_development_factors(age_to_age_factors: list[float]) -> list[float]:
    cdfs = [1.0 for _ in range(len(age_to_age_factors) + 1)]
    running = 1.0
    for index in range(len(age_to_age_factors) - 1, -1, -1):
        running *= age_to_age_factors[index]
        cdfs[index] = running
    return cdfs


def _latest_observed(row: list[float | None]) -> float:
    for value in reversed(row):
        if value is not None:
            return value
    return 0.0


def _latest_observed_index(row: list[float | None]) -> int | None:
    for index in range(len(row) - 1, -1, -1):
        if row[index] is not None:
            return index
    return None


def _round_optional_matrix(values: list[list[float | None]], digits: int) -> list[list[float | None]]:
    return [[None if value is None else round(value, digits) for value in row] for row in values]
