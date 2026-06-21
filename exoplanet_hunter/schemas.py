from typing import Any, Literal

from pydantic import BaseModel, Field


class Metadata(BaseModel):
    filename: str
    target_id: str | None = None
    mission: str | None = None
    telescope: str | None = None
    instrument: str | None = None
    object_name: str | None = None
    ra_deg: float | None = None
    dec_deg: float | None = None
    cadence: str | None = None
    exposure_time_seconds: float | None = None
    time_reference: str | None = None
    observation_start: str | None = None
    observation_end: str | None = None
    raw_header: dict[str, Any] = Field(default_factory=dict)


class CandidateStatistics(BaseModel):
    period_days: float | None = None
    epoch_days: float | None = None
    duration_days: float | None = None
    depth: float | None = None
    depth_ppm: float | None = None
    signal_to_noise: float | None = None
    odd_even_depth_difference: float | None = None
    observed_transit_count: int = 0
    points_in_transit: int = 0
    periodogram_power: float | None = None


class Candidate(BaseModel):
    label: str = "Candidate"
    rank: int
    confidence_score: float = Field(ge=0.0, le=1.0)
    statistics: CandidateStatistics
    reasons: list[str] = Field(default_factory=list)
    possible_false_positive_flags: list[str] = Field(default_factory=list)


class PlotProducts(BaseModel):
    target_pixel_image: str | None = None
    raw_light_curve: str | None = None
    flattened_light_curve: str | None = None
    binned_light_curve: str | None = None
    smoothed_light_curve: str | None = None
    periodogram: str | None = None
    folded_light_curve: str | None = None


class LightCurveSummary(BaseModel):
    point_count: int
    duration_days: float | None = None
    median_flux: float | None = None
    flux_scatter: float | None = None
    normalized: bool = True


class AnalysisResponse(BaseModel):
    analysis_id: str
    status: Literal["completed"]
    metadata: Metadata
    light_curve: LightCurveSummary
    best_candidate_periods_days: list[float]
    candidates: list[Candidate]
    plots: PlotProducts
    report_path: str
    processing_time_seconds: float = 0.0
    notes: list[str] = Field(default_factory=list)
