import gc
import logging
import time
from pathlib import Path

import numpy as np
from fastapi import UploadFile

from .candidates import build_candidates
from .config import Settings
from .fits_reader import extract_metadata, extract_target_pixel_image
from .io import cleanup_partial_run, cleanup_upload, create_run_dir, new_analysis_id, save_upload
from .lightcurve import bin_light_curve, load_light_curve, prepare_light_curve, smooth_flux
from .periodogram import compute_periodogram
from .plots import save_all_plots
from .reporting import save_json_report
from .schemas import AnalysisResponse, LightCurveSummary

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def analyze_upload(self, file: UploadFile) -> AnalysisResponse:
        analysis_id = new_analysis_id()
        run_dir = create_run_dir(self.settings, analysis_id)
        fits_path = None
        try:
            fits_path = await save_upload(file, self.settings, analysis_id)
            return self._run_analysis(fits_path, run_dir, analysis_id)
        except Exception:
            cleanup_partial_run(run_dir)
            raise
        finally:
            if fits_path:
                cleanup_upload(fits_path)

    def _run_analysis(self, fits_path: Path, run_dir: Path, analysis_id: str) -> AnalysisResponse:
        start_time = time.monotonic()
        metadata = extract_metadata(fits_path)
        pixel_image = extract_target_pixel_image(fits_path)
        raw_light_curve = load_light_curve(fits_path)
        prepared = prepare_light_curve(raw_light_curve, minimum_points=self.settings.minimum_points)
        del raw_light_curve
        gc.collect()
        binned = bin_light_curve(prepared.flattened)
        smoothed_time, smoothed_flux = smooth_flux(prepared.flattened)
        periodogram = compute_periodogram(prepared.flattened, method=self.settings.periodogram_method)
        candidates = build_candidates(prepared.flattened, periodogram)
        plots = save_all_plots(run_dir, pixel_image, prepared.raw, prepared.flattened, binned, smoothed_time, smoothed_flux, periodogram, dpi=self.settings.plot_dpi)
        del pixel_image, binned, smoothed_time, smoothed_flux
        gc.collect()
        response = AnalysisResponse(
            analysis_id=analysis_id,
            status="completed",
            metadata=metadata,
            light_curve=_summarize_light_curve(prepared.flattened),
            best_candidate_periods_days=periodogram.candidate_periods,
            candidates=candidates,
            plots=plots,
            report_path="",
            processing_time_seconds=round(time.monotonic() - start_time, 2),
            notes=[
                "Candidate classifications are statistical screening results only.",
                "No result should be interpreted as a confirmed planet without follow-up validation.",
            ],
        )
        response.report_path = save_json_report(response, run_dir / "analysis_report.json")
        logger.info("Analysis %s completed in %.1fs", analysis_id, response.processing_time_seconds)
        return response


def _summarize_light_curve(light_curve) -> LightCurveSummary:
    time = np.asarray(light_curve.time.value, dtype=float)
    flux = np.asarray(light_curve.flux.value if hasattr(light_curve.flux, "value") else light_curve.flux, dtype=float)
    return LightCurveSummary(
        point_count=int(len(time)),
        duration_days=float(np.nanmax(time) - np.nanmin(time)) if len(time) else None,
        median_flux=float(np.nanmedian(flux)) if len(flux) else None,
        flux_scatter=_robust_std(flux) if len(flux) else None,
        normalized=True,
    )


def _robust_std(values: np.ndarray) -> float:
    median = np.nanmedian(values)
    mad = np.nanmedian(np.abs(values - median))
    return float(1.4826 * mad) if np.isfinite(mad) and mad > 0 else float(np.nanstd(values))
