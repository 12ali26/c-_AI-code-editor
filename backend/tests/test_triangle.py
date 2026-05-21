from app.models import TriangleValueType
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
    assert triangle.validation_warnings == []

