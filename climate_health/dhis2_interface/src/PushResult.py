
import dataclasses
from typing import List
from climate_health.dhis2_interface.src.Config import ProgramConfig
from climate_health.dhis2_interface.src.HttpRequest import get_request_session
import logging
import dataclasses
import json
from dataclasses import asdict


logger = logging.getLogger(__name__)


@dataclasses.dataclass
class DataValue:
    value:int
    orgUnit:str
    dataElement:str
    period:str
    
def push_result(programConfig : ProgramConfig, dataValues : List[DataValue]):
    
    session = get_request_session(programConfig)

    data_list = [dataclasses.asdict(data_value) for data_value in dataValues]

    unique_elems = {(data['dataElement'], data['period'], data['orgUnit']) for data in data_list}
    assert len(unique_elems) == len(data_list), "DataValues must be unique"

    body = {'dataValues': data_list}

    url = f'{programConfig.dhis2Baseurl}/api/40/dataValueSets'
    
    try:
        response = session.post(url=url, json=body)
    except Exception as e:
        logger.error('Could not push CHAP-result to dhis 2: %s', e)
        raise
    if(response.status_code == 200):
        print(
            f"- 200 OK - successfully pushed CHAP-result"
        )
        return
    if (response.status_code != 201):
        raise Exception(f"Could not create. \nError code: {response.status_code} \n{response.json()}")
    
    print(
        f"- 201 OK - successfully pushed CHAP-result")
    response_json = response.json()
    return response_json