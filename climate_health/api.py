import logging
import json
import zipfile
from pathlib import Path
from typing import Optional, List

import numpy as np

from .assessment.dataset_splitting import train_test_split_with_weather
from .datatypes import HealthData, ClimateData, HealthPopulationData, SimpleClimateData, ClimateHealthData, FullData
from .dhis2_interface.json_parsing import predictions_to_datavalue, parse_disease_data, json_to_pandas, \
    parse_population_data
from .external.external_model import get_model_from_yaml_file
#from .external.external_model import ExternalCommandLineModel, get_model_from_yaml_file
from .geojson import geojson_to_shape, geojson_to_graph
from .predictor import get_model
from .spatio_temporal_data.temporal_dataclass import SpatioTemporalDict
import dataclasses

from .time_period.date_util_wrapper import Week, delta_week, delta_month, Month

logger = logging.getLogger(__name__)

@dataclasses.dataclass
class AreaPolygons:
    shape_file: str


@dataclasses.dataclass
class PredictionData:
    area_polygons: AreaPolygons = None
    health_data: SpatioTemporalDict[HealthData] = None
    climate_data: SpatioTemporalDict[ClimateData] = None
    population_data: SpatioTemporalDict[HealthPopulationData] = None


def read_zip_folder(zip_file_path: str) -> PredictionData:
    # read zipfile, create PredictionData
    ziparchive = zipfile.ZipFile(zip_file_path)
    expected_files = {
        "area_polygons": "orgUnits.json",
        "disease": "disease.json",
        "population": "population.json",
        "temperature": "temperature.json",
        "precipitation": "precipitation.json",
    }
    json_data = json.load(ziparchive.open(expected_files["disease"]))
    name_mapping = {
        "time_period": 2,
        "disease_cases": 3,
        "location": 1
    }
    disease = parse_disease_data(json_data, name_mapping=name_mapping)

    temperature_json = json.load(ziparchive.open(expected_files["temperature"]))
    name_mapping = {
        "time_period": 2,
        "mean_temperature": 3,
        "location": 1
    }
    temperature = json_to_pandas(temperature_json, name_mapping)

    precipitation_json = json.load(ziparchive.open(expected_files["temperature"]))
    name_mapping = {
        "time_period": 2,
        "precipitation": 3,
        "location": 1
    }
    precipitation = json_to_pandas(precipitation_json, name_mapping)

    assert np.all(precipitation.time_period == temperature.time_period)
    assert np.all(precipitation.location == temperature.location)

    temperature["rainfall"] = precipitation["precipitation"]
    temperature["rainfall"] = temperature["rainfall"].astype(float)
    temperature["mean_temperature"] = temperature["mean_temperature"].astype(float)
    climate = SpatioTemporalDict.from_pandas(temperature, dataclass=SimpleClimateData)

    population_json = json.load(ziparchive.open(expected_files["population"]))
    population = parse_population_data(population_json)
    graph_file_name = ''
    if False:
        graph_file_name = Path(zip_file_path).with_suffix(".graph")
        area_polygons_file = ziparchive.open(expected_files["area_polygons"])
        geojson_to_graph(area_polygons_file, graph_file_name)
    # geojson_to_shape(area_polygons_file, shape_file_name)

    # geojson_to_shape(str(zip_file_path) + "!area_polygons", shape_file_name)

    return PredictionData(
        health_data=disease,
        climate_data=climate,
        population_data=population,
        area_polygons=AreaPolygons(graph_file_name)
    )

    out_data = {}


#    ...

def get_model_maybe_yaml(model_name, dockername=None):
    if model_name.endswith(".yaml") or model_name.endswith(".yml"):

        model = get_model_from_yaml_file(model_name, dockername)
        return model, model.name
    else:
        return get_model(model_name), model_name


def dhis_zip_flow(zip_file_path: str, out_json: Optional[str]=None, model_name=None, n_months=4, docker_filename: Optional[str] = None) -> List[dict] | None:
    data: PredictionData = read_zip_folder(zip_file_path)
    json_body = train_on_prediction_data(data, model_name, n_months, docker_filename)
    if out_json is not None:
        with open(out_json, "w") as f:
            json.dump(json_body, f)
        return None
    else:
        return json_body


def train_on_prediction_data(data, model_name=None, n_months=4, docker_filename=None):
    model, model_name = get_model_maybe_yaml(model_name, docker_filename)
    model = model()
    start_endpoint = min(data.health_data.start_timestamp,
                         data.climate_data.start_timestamp)
    end_endpoint = max(data.health_data.end_timestamp,
                       data.climate_data.end_timestamp)
    new_dict = {}
    for location in data.health_data.locations():
        health = data.health_data.get_location(location).fill_to_range(start_endpoint, end_endpoint)
        climate = data.climate_data.get_location(location).fill_to_range(start_endpoint, end_endpoint)
        assert location in data.population_data, f"Location {location} not in population data: {data.population_data.keys()}"
        population = data.population_data[location]

        new_dict[location] = FullData.combine(health.data(), climate.data(), population)
    climate_health_data = SpatioTemporalDict(new_dict)
    prediction_start = Month(climate_health_data.end_timestamp) - n_months * delta_month
    train_data, _, future_weather = train_test_split_with_weather(climate_health_data, prediction_start)
    logger.info(f"Training model {model_name} on {len(train_data.items())} locations")
    model.train(climate_health_data)  # , extra_args=data.area_polygons)
    logger.info(f"Forecasting using {model_name} on {len(train_data.items())} locations")
    predictions = model.forecast(future_weather, forecast_delta=n_months * delta_month)
    attrs = ['median', 'quantile_high', 'quantile_low']
    logger.info(f"Converting predictions to json")
    data_values = predictions_to_datavalue(predictions, attribute_mapping=dict(zip(attrs, attrs)))
    json_body = [dataclasses.asdict(element) for element in data_values]
    return json_body
