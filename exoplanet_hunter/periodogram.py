from dataclasses import dataclass

import lightkurve as lk
import numpy as np
from astropy.timeseries import BoxLeastSquares, LombScargle


@dataclass
class PeriodogramResult:
    method: str
    periods: np.ndarray
    power: np.ndarray
    candidate_periods: list[float]
    candidate_powers: list[float]
    durations: list[float]
    transit_times: list[float | None]


def compute_periodogram(light_curve: lk.LightCurve, method: str = "auto", max_candidates: int = 5) -> PeriodogramResult:
    time = _time_values(light_curve)
    flux = _flux_values(light_curve)
    mask = np.isfinite(time) & np.isfinite(flux)
    time = time[mask]
    flux = flux[mask]
    if len(time) < 50:
        raise ValueError("Not enough finite light-curve points for period search.")

    baseline = np.nanmax(time) - np.nanmin(time)
    min_period = max(0.05, 2.0 * np.nanmedian(np.diff(np.sort(time))))
    max_period = max(min_period * 2, baseline / 2.0)
    if method == "lomb_scargle":
        return _lomb_scargle(time, flux - np.nanmedian(flux), min_period, max_period, max_candidates)
    return _bls(time, flux, min_period, max_period, max_candidates)


def _bls(time: np.ndarray, flux: np.ndarray, min_period: float, max_period: float, max_candidates: int) -> PeriodogramResult:
    n_points = len(time)
    n_periods = 4000 if n_points < 5000 else 8000
    periods = np.linspace(min_period, max_period, n_periods)
    cadence = max(np.nanmedian(np.diff(np.sort(time))), 1e-4)
    max_duration = min(0.5, max_period * 0.12, min_period * 0.9)
    min_duration = max(cadence, 0.02)
    if max_duration <= min_duration:
        max_duration = min_duration * 1.5
    durations = np.linspace(min_duration, max_duration, 12)
    result = BoxLeastSquares(time, flux).power(periods, durations)
    power = np.asarray(result.power, dtype=float)
    selected = _select_peak_indices(periods, power, max_candidates)
    return PeriodogramResult(
        method="bls",
        periods=periods,
        power=power,
        candidate_periods=[float(periods[idx]) for idx in selected],
        candidate_powers=[float(power[idx]) for idx in selected],
        durations=[float(np.asarray(result.duration)[idx]) for idx in selected],
        transit_times=[float(np.asarray(result.transit_time)[idx]) for idx in selected],
    )


def _lomb_scargle(time: np.ndarray, flux: np.ndarray, min_period: float, max_period: float, max_candidates: int) -> PeriodogramResult:
    frequency = np.linspace(1.0 / max_period, 1.0 / min_period, 8000)
    power = LombScargle(time, flux).power(frequency)
    periods = 1.0 / frequency
    order = np.argsort(periods)
    periods = periods[order]
    power = power[order]
    selected = _select_peak_indices(periods, power, max_candidates)
    return PeriodogramResult(
        method="lomb_scargle",
        periods=periods,
        power=power,
        candidate_periods=[float(periods[idx]) for idx in selected],
        candidate_powers=[float(power[idx]) for idx in selected],
        durations=[float(max(min_period, periods[idx] * 0.04)) for idx in selected],
        transit_times=[None for _ in selected],
    )


def _select_peak_indices(periods: np.ndarray, power: np.ndarray, max_candidates: int) -> np.ndarray:
    finite = np.isfinite(power) & np.isfinite(periods)
    ranked = np.argsort(power[finite])[::-1]
    finite_indices = np.where(finite)[0]
    selected: list[int] = []
    for idx in finite_indices[ranked]:
        period = periods[idx]
        if all(abs(period - periods[old]) / periods[old] > 0.03 for old in selected):
            selected.append(int(idx))
        if len(selected) >= max_candidates:
            break
    return np.asarray(selected, dtype=int)


def _time_values(light_curve: lk.LightCurve) -> np.ndarray:
    return np.asarray(light_curve.time.value, dtype=float)


def _flux_values(light_curve: lk.LightCurve) -> np.ndarray:
    return np.asarray(light_curve.flux.value if hasattr(light_curve.flux, "value") else light_curve.flux, dtype=float)
