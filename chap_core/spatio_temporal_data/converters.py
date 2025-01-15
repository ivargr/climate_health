import pandas as pd

from chap_core.spatio_temporal_data.temporal_dataclass import DataSet as _DataSet


def observations_to_dataset(dataclass, observations, fill_missing=False):
    dataframe = pd.DataFrame([obs.model_dump() for obs in observations]).rename(
        columns={'org_unit': 'location', 'period': 'time_period'})
    dataframe = dataframe.set_index(["location", "time_period"])
    pivoted = dataframe.pivot(columns="element_id", values="value").reset_index()
    new_dataset = _DataSet.from_pandas(pivoted, dataclass, fill_missing=fill_missing)
    return new_dataset
