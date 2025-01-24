from typing import List

from pydantic import BaseModel

from chap_core.database.base_tables import DBModel
from chap_core.database.dataset_tables import DataSetBase, ObservationBase


class PredictionBase(BaseModel):
    orgUnit: str
    dataElement: str
    period: str


class PredictionResponse(PredictionBase):
    value: float


class PredictionSamplResponse(PredictionBase):
    values: list[float]


class FullPredictionResponse(BaseModel):
    diseaseId: str
    dataValues: List[PredictionResponse]


class FullPredictionSampleResponse(BaseModel):
    diseaseId: str
    dataValues: List[PredictionSamplResponse]


class FetchRequest(DBModel):
    data_source_name: str



class DatasetMakeRequest(DataSetBase):
    provided_data: List[ObservationBase]
    data_to_be_fetched: List[FetchRequest]
