import pandas as pd
import pytest

from climate_health.assessment.prediction_evaluator import evaluate_model
from climate_health.dataset import IsSpatioTemporalDataSet
from climate_health.datatypes import ClimateHealthTimeSeries, HealthData
from climate_health.external.external_model import ExternalCommandLineModel
from climate_health.external.models import SSM
from climate_health.external.models.jax_models.simple_ssm import SSMWithLinearEffect
from climate_health.runners.command_line_runner import CommandLineRunner
from climate_health.spatio_temporal_data.temporal_dataclass import SpatioTemporalDict
from . import EXAMPLE_DATA_PATH, TEST_PATH


class MockExternalModel:
    pass


@pytest.fixture
def data_set_filename():
    return EXAMPLE_DATA_PATH / 'data.csv'


@pytest.fixture
def dataset_name():
    return 'hydro_met_subset'


@pytest.fixture()
def r_script_filename() -> str:
    return EXAMPLE_DATA_PATH / 'example_r_script.r'


@pytest.fixture()
def python_script_filename() -> str:
    return TEST_PATH / 'mock_predictor_script.py predict-values '


@pytest.fixture()
def python_model_train_command() -> str:
    return "python " + str(TEST_PATH / 'mock_predictor_script.py train {train_data} {model}')


@pytest.fixture()
def python_model_predict_command() -> str:
    return "python " + str(TEST_PATH / 'mock_predictor_script.py predict {future_data} {model} {out_file}')


@pytest.fixture()
def output_filename(tmp_path) -> str:
    return tmp_path / 'output.html'


@pytest.fixture
def load_data_func(data_path):
    def load_data_set(data_set_filename: str) -> IsSpatioTemporalDataSet:
        assert data_set_filename == 'hydro_met_subset'
        file_name = (data_path / data_set_filename).with_suffix('.csv')
        return SpatioTemporalDict.from_pandas(pd.read_csv(file_name), ClimateHealthTimeSeries)

    return load_data_set


class ExternalModelMock:

    def __init__(self, *args, **kwargs):
        pass

    def get_predictions(self, train_data: IsSpatioTemporalDataSet[ClimateHealthTimeSeries],
                        future_climate_data: IsSpatioTemporalDataSet[ClimateHealthTimeSeries]) -> \
            IsSpatioTemporalDataSet[HealthData]:
        period = next(iter(future_climate_data.data())).data().time_period[:1]
        new_dict = {loc: HealthData(period, data.data().disease_cases[-1:]) for loc, data in
                    train_data.items()}
        return SpatioTemporalDict(new_dict)


# @pytest.mark.xfail
def test_external_model_evaluation(dataset_name, output_filename, load_data_func, external_predictive_model):
    external_model = external_predictive_model
    data_set = load_data_func(dataset_name)
    report = evaluate_model(data_set, external_model)
    report.save(output_filename)


@pytest.mark.skip
@pytest.mark.parametrize('mode', ['forecast'])
def test_summary_model_evaluation(dataset_name, output_filename, load_data_func, mode):
    summary_model = SSM()
    model_class = SSMWithLinearEffect
    SSM.n_warmup = 10
    model_class.n_warmup = 10
    data_set = load_data_func(dataset_name)
    report, table = evaluate_model(data_set, summary_model,
                                   max_splits=2, naive_model_cls=model_class,
                                   mode=mode, return_table=True)
    table.to_csv('tmp.csv')
    for report in report.report:
        report.show()


@pytest.fixture()
def external_predictive_model(python_model_predict_command, python_model_train_command):
    runner = CommandLineRunner("./")
    external_model = ExternalCommandLineModel("external_model", python_model_train_command,
                                              python_model_predict_command, HealthData,
                                              runner=runner)

    return external_model
