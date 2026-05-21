from __future__ import annotations

from app.models import ReservingResult, Triangle


class ReservingError(ValueError):
    pass


def run_chain_ladder(triangle: Triangle, selected_factors: list[float] | None = None) -> ReservingResult:
    values = triangle.values
    if not values or not triangle.development_periods:
        raise ReservingError("Triangle has no values")

    factors = selected_factors or _volume_weighted_age_to_age(values)
    if len(factors) != len(triangle.development_periods) - 1:
        raise ReservingError("Selected factor count must equal development period count minus one")

    cdfs = _cumulative_development_factors(factors)
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
        "development_periods": triangle.development_periods,
        "origin_periods": triangle.origin_periods,
        "latest_observed_development_index": latest_indexes,
    }

    total_latest = round(sum(latest), 2)
    total_ultimate = round(sum(ultimates), 2)
    return ReservingResult(
        latest_diagonal=[round(value, 2) for value in latest],
        age_to_age_factors=[round(factor, 6) for factor in factors],
        cumulative_development_factors=[round(cdf, 6) for cdf in cdfs],
        ultimate_by_origin=ultimates,
        ibnr_by_origin=ibnr,
        total_latest=total_latest,
        total_ultimate=total_ultimate,
        total_ibnr=round(total_ultimate - total_latest, 2),
        diagnostics=diagnostics,
    )


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

