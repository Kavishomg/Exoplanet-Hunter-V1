import lightkurve as lk
import numpy as np

from .periodogram import PeriodogramResult
from .schemas import Candidate, CandidateStatistics


def build_candidates(light_curve: lk.LightCurve, periodogram: PeriodogramResult) -> list[Candidate]:
    time = _time_values(light_curve)
    flux = _flux_values(light_curve)
    scatter = _robust_std(flux)
    candidates: list[Candidate] = []
    for rank, period in enumerate(periodogram.candidate_periods, start=1):
        stats = compute_candidate_statistics(
            time=time,
            flux=flux,
            period=period,
            duration=periodogram.durations[rank - 1] if rank - 1 < len(periodogram.durations) else None,
            epoch=periodogram.transit_times[rank - 1] if rank - 1 < len(periodogram.transit_times) else None,
            scatter=scatter,
            power=periodogram.candidate_powers[rank - 1] if rank - 1 < len(periodogram.candidate_powers) else None,
        )
        flags = _false_positive_flags(stats, time)
        candidates.append(Candidate(
            rank=rank,
            confidence_score=_confidence_score(stats, flags),
            statistics=stats,
            reasons=_candidate_reasons(stats),
            possible_false_positive_flags=flags,
        ))
    return candidates


def compute_candidate_statistics(time, flux, period, duration, epoch, scatter, power) -> CandidateStatistics:
    if epoch is None or not np.isfinite(epoch):
        epoch = float(time[np.nanargmin(flux)])
    if duration is None or not np.isfinite(duration):
        duration = max(float(period * 0.04), float(np.nanmedian(np.diff(np.sort(time)))))
    phase = fold_phase(time, period, epoch)
    half_width = max(duration / period / 2.0, 0.002)
    in_transit = np.abs(phase) <= half_width
    baseline = float(np.nanmedian(flux[~in_transit])) if (~in_transit).any() else float(np.nanmedian(flux))
    transit_flux = float(np.nanmedian(flux[in_transit])) if in_transit.any() else float(np.nanmin(flux))
    depth = max(0.0, baseline - transit_flux)
    points = int(np.sum(in_transit))
    snr = float(depth / scatter * np.sqrt(max(points, 1))) if scatter > 0 and np.isfinite(scatter) else None
    return CandidateStatistics(
        period_days=float(period),
        epoch_days=float(epoch),
        duration_days=float(duration),
        depth=float(depth),
        depth_ppm=float(depth * 1_000_000),
        signal_to_noise=snr,
        odd_even_depth_difference=_odd_even_depth_difference(time, flux, period, epoch, duration),
        observed_transit_count=_observed_transit_count(time, period, epoch),
        points_in_transit=points,
        periodogram_power=float(power) if power is not None and np.isfinite(power) else None,
    )


def fold_phase(time: np.ndarray, period: float, epoch: float) -> np.ndarray:
    return ((time - epoch + 0.5 * period) % period) / period - 0.5


def _candidate_reasons(stats: CandidateStatistics) -> list[str]:
    reasons = []
    if stats.periodogram_power is not None:
        reasons.append("Strong periodogram peak relative to searched periods.")
    if stats.depth_ppm is not None and stats.depth_ppm > 100:
        reasons.append("Repeated dimming signal is measurable in the folded light curve.")
    if stats.signal_to_noise is not None and stats.signal_to_noise >= 6:
        reasons.append("Transit-window signal-to-noise is elevated.")
    if stats.observed_transit_count >= 2:
        reasons.append("Multiple transit-like events occur at the candidate period.")
    return reasons or ["Weak periodic signal retained for human review."]


def _false_positive_flags(stats: CandidateStatistics, time: np.ndarray) -> list[str]:
    flags = []
    baseline = float(np.nanmax(time) - np.nanmin(time)) if len(time) else 0.0
    if stats.observed_transit_count < 2:
        flags.append("Only one observed event; period is poorly constrained.")
    if stats.depth_ppm is not None and stats.depth_ppm > 50_000:
        flags.append("Very deep signal may indicate eclipsing binary or instrumental contamination.")
    if stats.odd_even_depth_difference is not None and stats.odd_even_depth_difference > 0.25:
        flags.append("Odd/even transit depth mismatch may indicate eclipsing binary.")
    if stats.period_days is not None and baseline and stats.period_days > baseline / 2:
        flags.append("Candidate period is close to the observation baseline.")
    if stats.signal_to_noise is not None and stats.signal_to_noise < 6:
        flags.append("Low signal-to-noise candidate.")
    return flags


def _confidence_score(stats: CandidateStatistics, flags: list[str]) -> float:
    score = 0.15
    if stats.periodogram_power is not None:
        score += 0.20
    if stats.signal_to_noise is not None:
        score += min(0.30, max(0.0, stats.signal_to_noise / 30.0))
    if stats.observed_transit_count >= 2:
        score += 0.15
    if stats.observed_transit_count >= 3:
        score += 0.10
    if stats.depth_ppm is not None and 50 <= stats.depth_ppm <= 50_000:
        score += 0.10
    score -= min(0.35, 0.08 * len(flags))
    return round(float(np.clip(score, 0.0, 0.95)), 3)


def _observed_transit_count(time, period, epoch) -> int:
    first = int(np.floor((np.nanmin(time) - epoch) / period))
    last = int(np.ceil((np.nanmax(time) - epoch) / period))
    return max(0, last - first + 1)


def _odd_even_depth_difference(time, flux, period, epoch, duration) -> float | None:
    transit_number = np.floor((time - epoch) / period).astype(int)
    phase = fold_phase(time, period, epoch)
    in_transit = np.abs(phase) <= max(duration / period / 2.0, 0.002)
    odd = in_transit & (transit_number % 2 != 0)
    even = in_transit & (transit_number % 2 == 0)
    if odd.sum() < 3 or even.sum() < 3:
        return None
    baseline = np.nanmedian(flux[~in_transit]) if (~in_transit).any() else np.nanmedian(flux)
    odd_depth = baseline - np.nanmedian(flux[odd])
    even_depth = baseline - np.nanmedian(flux[even])
    return float(abs(odd_depth - even_depth) / max(abs(odd_depth), abs(even_depth), 1e-12))


def _robust_std(values: np.ndarray) -> float:
    median = np.nanmedian(values)
    mad = np.nanmedian(np.abs(values - median))
    return float(1.4826 * mad) if np.isfinite(mad) and mad > 0 else float(np.nanstd(values))


def _time_values(light_curve: lk.LightCurve) -> np.ndarray:
    return np.asarray(light_curve.time.value, dtype=float)


def _flux_values(light_curve: lk.LightCurve) -> np.ndarray:
    return np.asarray(light_curve.flux.value if hasattr(light_curve.flux, "value") else light_curve.flux, dtype=float)
