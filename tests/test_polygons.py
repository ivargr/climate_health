import pytest
import tempfile
from chap_core.geometry import Polygons


def test_to_from_geojson_file(data_path):
    polygons = Polygons.from_file(data_path / "example_polygons.geojson")

    with tempfile.NamedTemporaryFile() as f:
        polygons.to_file(f.name)
        polygons2 = Polygons.from_file(f.name)

        assert polygons2 == polygons


