from __future__ import annotations

from io import BytesIO, StringIO

import pandas as pd

from app.models import Triangle, TriangleValueType


class TriangleParseError(ValueError):
    pass


def parse_triangle_file(
    content: bytes,
    filename: str,
    organization_id: str,
    dataset_id: str,
    origin_column: str,
    value_type: TriangleValueType,
) -> tuple[list[str], Triangle]:
    frame = _read_frame(content, filename)
    if origin_column not in frame.columns:
        raise TriangleParseError(f"Origin column '{origin_column}' was not found")

    development_columns = [column for column in frame.columns if column != origin_column]
    if not development_columns:
        raise TriangleParseError("At least one development period column is required")

    origin_periods = [str(value) for value in frame[origin_column].tolist()]
    values: list[list[float | None]] = []
    warnings: list[str] = []

    seen_origins: set[str] = set()
    for row_index, origin in enumerate(origin_periods):
        if origin in seen_origins:
            warnings.append(f"Duplicate origin period '{origin}'")
        seen_origins.add(origin)

        row_values: list[float | None] = []
        for column in development_columns:
            raw_value = frame.iloc[row_index][column]
            if pd.isna(raw_value) or raw_value == "":
                row_values.append(None)
                continue
            try:
                numeric_value = float(raw_value)
            except (TypeError, ValueError) as exc:
                raise TriangleParseError(
                    f"Cell at origin '{origin}', development '{column}' is not numeric"
                ) from exc
            if numeric_value < 0 and value_type != TriangleValueType.earned_premium:
                warnings.append(f"Negative value at origin '{origin}', development '{column}'")
            row_values.append(numeric_value)
        values.append(row_values)

    warnings.extend(_validate_triangle_shape(values))
    triangle = Triangle(
        organization_id=organization_id,
        dataset_id=dataset_id,
        origin_periods=origin_periods,
        development_periods=[str(column) for column in development_columns],
        values=values,
        validation_warnings=warnings,
    )
    return [str(column) for column in development_columns], triangle


def validation_summary(triangle: Triangle) -> dict[str, object]:
    return {
        "dataset_id": triangle.dataset_id,
        "triangle_id": triangle.id,
        "valid": len([warning for warning in triangle.validation_warnings if "not numeric" in warning]) == 0,
        "warnings": triangle.validation_warnings,
        "origin_periods": len(triangle.origin_periods),
        "development_periods": len(triangle.development_periods),
    }


def _read_frame(content: bytes, filename: str) -> pd.DataFrame:
    lower_name = filename.lower()
    if lower_name.endswith(".csv"):
        return pd.read_csv(StringIO(content.decode("utf-8-sig")))
    if lower_name.endswith(".xlsx") or lower_name.endswith(".xls"):
        return pd.read_excel(BytesIO(content))
    raise TriangleParseError("Only CSV and Excel files are supported")


def _validate_triangle_shape(values: list[list[float | None]]) -> list[str]:
    warnings: list[str] = []
    for row_index, row in enumerate(values):
        seen_blank = False
        for col_index, value in enumerate(row):
            if value is None:
                seen_blank = True
            elif seen_blank:
                warnings.append(
                    f"Origin row {row_index + 1} has a value after a missing cell at development column {col_index + 1}"
                )
                break
    return warnings

