from typing import Literal

from pydantic import BaseModel, Field


class RecommendationBaseModel(BaseModel):
    """Operational and environmental metrics for an airfield."""

    runway_direction: list[int] = Field(
        description="Runways direction."
    )
    runway_distance: list[int] = Field(
        description="Landing roll distance computed for current conditions, in feet."
    )  # versus runway length
    crosswind_speed: list[float] = Field(
        description="The computed crosswind component acting perpendicular to the runway centerline (in knots)."
    )  # versus crosswind limits for aircraft
    headwind_speed: list[float] = Field(
        description="The computed tailwind component acting along the runway in the opposite direction as "
                    "the aircraft's movement (in knots)."
    )
    visibility: int = Field(
        description="The prevailing horizontal visibility at the airfield, expressed in meters."
    )  # versus minimum for VFR/IFR flight
    cloud_base: int = Field(
        description="The height of the lowest cloud layer above ground level (AGL) that covers more "
                    "than half of the sky, expressed in feet."
    )  # versus minimum for VFR/IFR flight


class RecommendationExtendModel(RecommendationBaseModel):
    """Extends recommendation base model with a computed recommendation."""

    recommendation: Literal["NO GO", "GO IFR", "GO VFR"] = Field(
        default="NO GO",
        description="Flight recommendation based on the briefing."
    )


class RecommendationFinalModel(BaseModel):
    """
    Wrapper model representing the complete flight recommendation
    including both departure and arrival assessments and the
    overall go/no-go decision.
    """

    departure: RecommendationExtendModel
    arrival: RecommendationExtendModel
    final_recommendation: Literal["NO GO", "GO IFR", "GO VFR"]
