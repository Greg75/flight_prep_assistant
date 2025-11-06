from pydantic import BaseModel, Field

from .aircraft import AircraftModel
from .airfield import AirfieldModel, RunwayModel, FrequencyModel, WindModel
from .api import ApiParams, AircraftParams, AirfieldParams
from .briefing import BriefingModel
from .recommendation import RecommendationBaseModel, RecommendationExtendModel, RecommendationFinalModel
from .request_data import InputData


class OpsCalculatorInputData(BaseModel):
    aircraft_data: AircraftModel = Field(description="")
    airfield_data: AirfieldModel = Field(description="")


__all__ = ["AircraftModel", "AirfieldModel", "ApiParams", "AircraftParams", "AirfieldParams", "BriefingModel",
           "RecommendationBaseModel", "RecommendationExtendModel", "RecommendationFinalModel", "InputData",
           "RunwayModel", "FrequencyModel", "WindModel"]
