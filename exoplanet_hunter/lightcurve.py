from pathlib import Path

import lightkurve as lk
import numpy as np
from astropy.stats import sigma_clip
from scipy.ndimage import median_filter


class PreparedLightCurve:
    def __init__(self, raw: lk.LightCurve, flattened: lk.LightCurve):
        self.raw = raw
        self.flattened = flattened


def load_light_curve(path: Path) -> lk.LightCurve:
    try:
        product = lk.read(path)
    except Exception as exc:
        raise ValueError(
            f"Could not read FITS file: {exc}\n\n"
            "This file is not a supported TESS/Kepler data product. "
            "Supported files: Target Pixel Files (TPF) or Light Curve files from TESS or Kepler.\n\n"
            "Where to get working files:\n"
            "  - MAST Portal: https://mast.stsci.edu (search by TIC/Kepler ID, download TPF or LightCurve)\n"
            "  - Lightkurve examples: https://docs.lightkurve.org\n\n"
            "Tip: On MAST, look for products labeled 'Target Pixel' or 'Light Curve' — "
            "not Full Frame Images, target tables, or other data products."
        ) from exc
    light_curve = product.to_lightcurve(aperture_mask="pipeline") if hasattr(product, "to_lightcurve") else product
    if not isinstance(light_curve, lk.LightCurve):
        raise ValueError(
            "Uploaded FITS file did not contain a readable light curve. "
            "Please upload a Target Pixel File (TPF) or Light Curve file from TESS or Kepler."
        )
    return light_curve


def prepare_light_curve(light_curve: lk.LightCurve, minimum_points: int) -> PreparedLightCurve:
    raw = light_curve.copy()
    clean = _normalize_flux(light_curve.remove_nans())
    clean = _remove_flux_outliers(clean)
    if len(clean.time) < minimum_points:
        raise ValueError(f"Light curve has too few valid points; need at least {minimum_points}.")
    try:
        flattened = clean.flatten(window_length=_safe_window_length(len(clean.time)))
    except Exception:
        flattened = clean
    flattened = _normalize_flux(flattened).remove_nans()
    del clean
    return PreparedLightCurve(raw=raw, flattened=flattened)


def bin_light_curve(light_curve: lk.LightCurve, bins: int = 300) -> lk.LightCurve:
    if len(light_curve.time) <= bins:
        return light_curve.copy()
    time = _time_values(light_curve)
    cadence = np.nanmedian(np.diff(np.sort(time)))
    bin_size = max(np.ptp(time) / bins, cadence)
    try:
        return light_curve.bin(time_bin_size=bin_size)
    except Exception:
        return light_curve.copy()


def smooth_flux(light_curve: lk.LightCurve, kernel_size: int = 11) -> tuple[np.ndarray, np.ndarray]:
    time = _time_values(light_curve)
    flux = _flux_values(light_curve)
    if len(flux) < 3:
        return time, flux
    size = min(kernel_size, len(flux) if len(flux) % 2 else len(flux) - 1)
    return time, median_filter(flux, size=max(size, 3), mode="nearest")


def _normalize_flux(light_curve: lk.LightCurve) -> lk.LightCurve:
    try:
        return light_curve.normalize()
    except Exception:
        flux = _flux_values(light_curve)
        median = np.nanmedian(flux)
        if not np.isfinite(median) or median == 0:
            return light_curve
        normalized = light_curve.copy()
        normalized.flux = normalized.flux / median
        return normalized


def _remove_flux_outliers(light_curve: lk.LightCurve) -> lk.LightCurve:
    clipped = sigma_clip(_flux_values(light_curve), sigma=7, maxiters=3)
    mask = ~np.asarray(clipped.mask)
    return light_curve[mask] if mask.sum() >= 0.8 * len(mask) else light_curve


def _safe_window_length(point_count: int) -> int:
    length = max(11, int(point_count * 0.03))
    if length % 2 == 0:
        length += 1
    return min(length, point_count - 1 if point_count % 2 == 0 else point_count)


def _time_values(light_curve: lk.LightCurve) -> np.ndarray:
    return np.asarray(light_curve.time.value, dtype=float)


def _flux_values(light_curve: lk.LightCurve) -> np.ndarray:
    return np.asarray(light_curve.flux.value if hasattr(light_curve.flux, "value") else light_curve.flux, dtype=float)
