import pandas as pd
import numpy as np
import bionumpy as bnp
import pytest
from bionumpy.util.testing import assert_bnpdataclass_equal
from climate_health.datatypes import ClimateHealthTimeSeries, HealthData
from climate_health.spatio_temporal_data.temporal_dataclass import SpatioTemporalDict
from climate_health.time_period import PeriodRange
from climate_health.time_period.dataclasses import Year


def test_climate_health_time_series_from_csv(tmp_path):
    """Test the from_csv method."""
    data = pd.DataFrame(
        {
            "time_period": ["2010", "2011", "2012"],
            "rainfall": [1.0, 2.0, 3.0],
            "mean_temperature": [1.0, 2.0, 3.0],
            "disease_cases": [1, 2, 3],
        }
    )
    csv_file = tmp_path / "test.csv"
    data.to_csv(csv_file, index=False)
    ts = ClimateHealthTimeSeries.from_csv(csv_file)
    true_periods = PeriodRange.from_strings(['2010', '2011', '2012'])
    # bnp_ragged_array = true_periods
    # assert ts.time_period == bnp_ragged_array
    assert all(ts.time_period == true_periods)
    # assert_bnpdataclass_equal(ts.time_period, bnp_ragged_array)
    np.testing.assert_array_equal(ts.rainfall, np.array([1.0, 2.0, 3.0]))
    np.testing.assert_array_equal(ts.mean_temperature, np.array([1.0, 2.0, 3.0]))
    np.testing.assert_array_equal(ts.disease_cases, np.array([1, 2, 3]))


def test_climate_health_time_series_to_csv(tmp_path):
    """Test the to_csv method."""
    ts = ClimateHealthTimeSeries(
        time_period=PeriodRange.from_strings(['2010', '2011', '2012']),
        rainfall=np.array([1.0, 2.0, 3.0]),
        mean_temperature=np.array([1.0, 2.0, 3.0]),
        disease_cases=np.array([1, 2, 3]),
    )
    csv_file = tmp_path / "test.csv"
    ts.to_csv(csv_file)
    ts2 = ClimateHealthTimeSeries.from_csv(csv_file)
    assert ts == ts2
    # assert ts == ts2


@pytest.fixture()
def dataset_with_missing(data_path):
    return pd.read_csv(data_path / 'laos_pulled_data.csv')

#@pytest.mark.skip('Must be fixed!!!!!!')
def test_dataset_with_missing(dataset_with_missing):
    health_data = SpatioTemporalDict.from_pandas(dataset_with_missing, dataclass=HealthData, fill_missing=True)
    start = health_data.start_timestamp
    end = health_data.end_timestamp
    for location, data in health_data.items():
        # assert data.start_timestamp == start
        assert data.end_timestamp == end
