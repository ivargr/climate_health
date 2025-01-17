from typing import List, Annotated

import chap_core.rest_api_src.db_worker_functions as wf
import numpy as np
from pydantic import BaseModel, confloat

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from sqlmodel import Session

from chap_core.api_types import EvaluationEntry, DataList, DataElement, PredictionEntry
from chap_core.database.base_tables import DBModel
from chap_core.datatypes import FullData, HealthPopulationData
from chap_core.spatio_temporal_data.converters import dataset_model_to_dataset
from .crud import JobResponse, DatasetCreate
from .dependencies import get_session, get_database_url, get_settings
from chap_core.database.tables import BackTest
from chap_core.database.dataset_tables import DataSet
import logging

from ...celery_tasks import CeleryPool

router = APIRouter(prefix="/analytics", tags=["analytics"])

logger = logging.getLogger(__name__)
worker = CeleryPool()


class EvaluationEntryRequest(BaseModel):
    backtest_id: int
    quantiles: List[confloat(ge=0, le=1)]


@router.get("/evaluation-entry", response_model=List[EvaluationEntry])
async def get_evaluation_entries(
        backtest_id: Annotated[int, Query(alias="backtestId")],
        quantiles: List[float] = Query(...),
        session: Session = Depends(get_session)):
    backtest = session.get(BackTest, backtest_id)
    if backtest is None:
        raise HTTPException(status_code=404, detail="BackTest not found")
    return [
        EvaluationEntry(period=forecast.period, orgUnit=forecast.org_unit, quantile=q,
                        splitPeriod=forecast.last_seen_period,
                        value=np.quantile(forecast.values, q)) for forecast in backtest.forecasts for q in
        quantiles
    ]


class PredictionCreate(DatasetCreate):
    model_id: str


@router.post('/prediction', response_model=JobResponse)
async def make_prediction(dataset: PredictionCreate,
                          datababase_url=Depends(get_database_url),
                          worker_settings=Depends(get_settings)):
    model_id = dataset.model_id
    data = dataset_model_to_dataset(HealthPopulationData, dataset)

    job = worker.queue_db(wf.predict_pipeline_from_health_dataset,
                          data.model_dump(), dataset.name, model_id,
                          database_url=datababase_url, worker_config=worker_settings)

    return JobResponse(id=job.id)


@router.get("/prediction-entry/{predictionId}", response_model=List[PredictionEntry])
def get_prediction_entries(prediction_id: Annotated[int, Path(alias="predictionId")],
                           session: Session = Depends(get_session)):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/actual-cases/{backtestId}", response_model=DataList)
async def get_actual_cases(backtest_id: Annotated[int, Path(alias="backtestId")],
                           session: Session = Depends(get_session)):
    backtest = session.get(BackTest, backtest_id)
    logger.info(f"Backtest: {backtest}")
    data = session.get(DataSet, backtest.dataset_id)
    logger.info(f"Data: {data}")
    if backtest is None:
        raise HTTPException(status_code=404, detail="BackTest not found")
    data_list = [DataElement(pe=observation.period, ou=observation.org_unit, value=float(observation.value) if not (
            np.isnan(observation.value) or observation.value is None) else None) for
                 observation in data.observations if observation.element_id == "disease_cases"]
    logger.info(f"DataList: {len(data_list)}")
    return DataList(
        featureId="disease_cases",
        dhis2Id="disease_cases",
        data=data_list
    )
