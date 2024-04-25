import os
from pathlib import Path

import pytest
from climate_health.geojson import geojson_to_shape
from . import EXAMPLE_DATA_PATH
from tempfile import NamedTemporaryFile


@pytest.fixture
def geojson_example_file():
    return EXAMPLE_DATA_PATH / "Organisation units.geojson"


def test_geojson_to_shape(geojson_example_file):
    # this does not work with temporarifles, as a real directory is needed
    out = "shapefile_test"
    geojson_to_shape(geojson_example_file, out + ".shp")

    extensions = [".cpg", ".dbf", ".prj", ".shp", ".shx"]
    for extension in extensions:
        assert os.path.isfile(out + extension)
        os.remove(out + extension)


