import datetime
import json
import logging
from typing import Iterable, List
import ee
import dataclasses
import enum
import os
from array import array
import zipfile

from pydantic import BaseModel

from climate_health.climate_data.gee import parse_gee_properties
from climate_health.datatypes import ClimateData
from climate_health.spatio_temporal_data.temporal_dataclass import SpatioTemporalDict
from climate_health.time_period.date_util_wrapper import PeriodRange, TimePeriod
from typing import List
import ee

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def meter_to_mm(m):
    return round(m * 1000, 3)

def round_two_decimal(v):
    return round(v, 2)

def kelvin_to_celsium(v):
    return round_two_decimal(v - 273.15)

@dataclasses.dataclass
class Band:
    name: str
    reducer: str
    converter: callable
    indicator : str
    periodeReducer : str

bands = [
    Band(name="temperature_2m", reducer="mean", periodeReducer="mean", converter=kelvin_to_celsium, indicator = "mean_temperature"),
    Band(name="total_precipitation_sum", reducer="mean", periodeReducer="sum", converter=meter_to_mm, indicator = "rainfall")
]

@dataclasses.dataclass
class Periode:
    id: str
    startDate : datetime
    endDate : datetime

class GoogleEarthEngine(BaseModel):
    
    def __init__(self):
        self.initializeClient()

    def initializeClient(self):
        #read environment variables
        account = os.environ.get('GOOGLE_SERVICE_ACCOUNT_EMAIL')
        private_key = os.environ.get('GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY')

        if(not account):
            logger.warn("GOOGLE_SERVICE_ACCOUNT_EMAIL is not set, you need to set it in the environment variables to use Google Earth Engine")
        if(not private_key):
            logger.warn("GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY is not set, you need to set it in the environment variables to use Google Earth Engine")

        if(not account or not private_key):
            return
        
        try:
            credentials = ee.ServiceAccountCredentials(account, key_data=private_key)
            ee.Initialize(credentials)
            logger.info("Google Earth Engine initialized, with account: "+account)
        except ValueError as e:
            logger.error("\nERROR:\n", e, "\n")


    def fetch_historical_era5_from_gee(self, zip_file_path: str, periodes : Iterable[Periode]) -> SpatioTemporalDict[ClimateData]:
        features = self.get_feature_from_zip(zip_file_path)

        #Fetch data for all bands
        gee_result = self.fetch_data_climate_indicator(features, periodes, bands)

        return parse_gee_properties(gee_result)

         
    def get_feature_from_zip(self, zip_file_path: str):
        ziparchive = zipfile.ZipFile(zip_file_path)
        features = json.load(ziparchive.open("orgUnits.geojson"))["features"]
        return features
    

    def fetch_data_climate_indicator(self, features, periodes : Iterable[TimePeriod], bands : List[Band]) -> SpatioTemporalDict[ClimateData]:
        
        eeReducerType = "mean"

        collection = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR').select([band.name for band in bands])
        featureCollection : ee.FeatureCollection = ee.FeatureCollection(features)

        #Creates a ee.List for every periode, containing id (periodeId), start_date and end_date for each period
        periodeList = ee.List([ee.Dictionary({"period" : p.id, "start_date" : p.start_timestamp.date, "end_date" : p.end_timestamp.date}) for p in periodes])
    
        eeScale = collection.first().select(0).projection().nominalScale()
        eeReducer = getattr(ee.Reducer, eeReducerType)()

        #Get every dayli image that exisist within a periode, and reduce it to a periodeReducer value
        def getPeriode(p, band : Band) -> ee.Image:
            p = ee.Dictionary(p)
            start = ee.Date(p.get("start_date"))
            end = ee.Date(p.get("end_date")).advance(-1, "day") #remove one day, since the end date is inclusive on current format?

            #Get only images from start to end, for one bands
            filtered : ee.ImageCollection = collection.filterDate(start, end).select(band.name)

            #Aggregate the imageCollection to one image, based on the periodeReducer
            return getattr(filtered, band.periodeReducer)() \
                .set("system:period", p.get("period")) \
                .set("system:time_start", start.millis()) \
                .set("system:time_end", end.millis()) \
                .set("system:indicator", band.indicator)


        dailyCollection = ee.ImageCollection([])

        #Map the bands, then the periodeList for each band, and return the aggregated Image to the ImageCollection
        for b in bands:
            dailyCollection = dailyCollection.merge(ee.ImageCollection.fromImages(
                periodeList.map(lambda period : getPeriode(period, b))
            ).filter(ee.Filter.listContains("system:band_names", b.name)))  # Remove empty images

        #Reduce the result, to contain only, orgUnitId, periodeId and the value
        reduced = dailyCollection.map(lambda image: 
            image.reduceRegions(
                collection=featureCollection,
                reducer=eeReducer,
                scale=eeScale
            ).map(lambda feature: 
                ee.Feature(
                    None, 
                    {
                        'ou': feature.id(),
                        'period': image.get('system:period'),
                        'value' : feature.get(eeReducerType),
                        'indicator' : image.get('system:indicator')
                    }
                )
            )
        ).flatten()

        valueCollection : ee.FeatureCollection = ee.FeatureCollection(reduced)

        size = valueCollection.size().getInfo()
        result : List = []
        take = 5_000

        #Keeps every f.properties, and replace the band values with the converted values
        def dataParser(data, bands : List[Band]):
            parsed_data = [{**f['properties'],
                                #Using the right converter on the value, based on the whats defined as band-converter
                                **{'value': next(b.converter for b in bands if f['properties']['indicator'] == b.indicator)(f['properties']['value'])}}
                                for f in data]
            return parsed_data


        for i in range(0, size, take):     
            result = result + (valueCollection.toList(take, i).getInfo())
            logger.log(logging.INFO, f" Fetched {i+take} of {size}")

    
        parsedResult = dataParser(result, bands)

        return parsedResult











        