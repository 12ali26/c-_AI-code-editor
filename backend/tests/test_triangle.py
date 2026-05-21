from app.models import TriangleBasis, TriangleValueType
from app.services.triangle import parse_triangle_file


def test_parse_triangle_csv_normalizes_values_and_warnings() -> None:
    csv = b"origin_period,12,24,36\n2022,100,150,175\n2023,120,180,\n"

    development_columns, triangle = parse_triangle_file(
        content=csv,
        filename="triangle.csv",
        organization_id="org",
        dataset_id="data",
        origin_column="origin_period",
        value_type=TriangleValueType.paid,
    )

    assert development_columns == ["12", "24", "36"]
    assert triangle.origin_periods == ["2022", "2023"]
    assert triangle.values[1] == [120.0, 180.0, None]
    assert triangle.source_values[1] == [120.0, 180.0, None]
    assert triangle.triangle_basis == TriangleBasis.cumulative
    assert triangle.validation_warnings == []


def test_parse_incremental_triangle_converts_to_cumulative_values() -> None:
    csv = b"origin_period,12,24,36\n2022,100,50,25\n2023,120,60,\n"

    _, triangle = parse_triangle_file(
        content=csv,
        filename="triangle.csv",
        organization_id="org",
        dataset_id="data",
        origin_column="origin_period",
        value_type=TriangleValueType.paid,
        triangle_basis=TriangleBasis.incremental,
    )

    assert triangle.triangle_basis == TriangleBasis.incremental
    assert triangle.source_values == [[100.0, 50.0, 25.0], [120.0, 60.0, None]]
    assert triangle.values == [[100.0, 150.0, 175.0], [120.0, 180.0, None]]
