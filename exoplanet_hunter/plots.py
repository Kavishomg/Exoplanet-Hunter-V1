from pathlib import Path

import lightkurve as lk
import matplotlib
import numpy as np

from .candidates import fold_phase
from .periodogram import PeriodogramResult
from .schemas import PlotProducts

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def save_all_plots(run_dir: Path, pixel_image, raw, flattened, binned, smoothed_time, smoothed_flux, periodogram, dpi: int = 100) -> PlotProducts:
    products = PlotProducts()
    if pixel_image is not None:
        products.target_pixel_image = _plot_target_pixel_image(pixel_image, run_dir / "target_pixel_image.png", dpi)
    products.raw_light_curve = _plot_light_curve(raw, run_dir / "raw_light_curve.png", "Raw Light Curve", dpi)
    products.flattened_light_curve = _plot_light_curve(flattened, run_dir / "flattened_light_curve.png", "Flattened Light Curve", dpi)
    products.binned_light_curve = _plot_light_curve(binned, run_dir / "binned_light_curve.png", "Binned Light Curve", dpi)
    products.smoothed_light_curve = _plot_smoothed(smoothed_time, smoothed_flux, run_dir / "smoothed_light_curve.png", dpi)
    products.periodogram = _plot_periodogram(periodogram, run_dir / "periodogram.png", dpi)
    if periodogram.candidate_periods:
        products.folded_light_curve = _plot_folded(flattened, periodogram.candidate_periods[0], periodogram.transit_times[0], run_dir / "folded_light_curve.png", dpi)
    return products


def _plot_target_pixel_image(image, path: Path, dpi: int) -> str:
    plt.figure(figsize=(6, 5))
    plt.imshow(image, origin="lower", cmap="viridis")
    plt.colorbar(label="Flux")
    plt.title("Target Pixel Image")
    plt.xlabel("Pixel Column")
    plt.ylabel("Pixel Row")
    return _save(path, dpi)


def _plot_light_curve(light_curve: lk.LightCurve, path: Path, title: str, dpi: int) -> str:
    plt.figure(figsize=(10, 4))
    plt.scatter(_time_values(light_curve), _flux_values(light_curve), s=5, alpha=0.65, linewidths=0)
    plt.title(title)
    plt.xlabel("Time [days]")
    plt.ylabel("Normalized Flux")
    return _save(path, dpi)


def _plot_smoothed(time, flux, path: Path, dpi: int) -> str:
    plt.figure(figsize=(10, 4))
    plt.plot(time, flux, linewidth=1.4)
    plt.title("Smoothed Light Curve")
    plt.xlabel("Time [days]")
    plt.ylabel("Normalized Flux")
    return _save(path, dpi)


def _plot_periodogram(periodogram: PeriodogramResult, path: Path, dpi: int) -> str:
    plt.figure(figsize=(10, 4))
    plt.plot(periodogram.periods, periodogram.power, linewidth=1.1)
    for period in periodogram.candidate_periods[:3]:
        plt.axvline(period, color="crimson", alpha=0.55, linestyle="--")
    plt.title(f"{periodogram.method.upper()} Periodogram")
    plt.xlabel("Period [days]")
    plt.ylabel("Power")
    return _save(path, dpi)


def _plot_folded(light_curve: lk.LightCurve, period: float, epoch: float | None, path: Path, dpi: int) -> str:
    time = _time_values(light_curve)
    flux = _flux_values(light_curve)
    if epoch is None:
        epoch = float(time[np.nanargmin(flux)])
    phase = fold_phase(time, period, epoch)
    order = np.argsort(phase)
    plt.figure(figsize=(8, 4.5))
    plt.scatter(phase[order], flux[order], s=6, alpha=0.65, linewidths=0)
    plt.title(f"Folded Light Curve: {period:.5g} days")
    plt.xlabel("Phase")
    plt.ylabel("Normalized Flux")
    return _save(path, dpi)


def _save(path: Path, dpi: int) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=dpi)
    plt.close()
    return str(path.as_posix())


def _time_values(light_curve: lk.LightCurve) -> np.ndarray:
    return np.asarray(light_curve.time.value, dtype=float)


def _flux_values(light_curve: lk.LightCurve) -> np.ndarray:
    return np.asarray(light_curve.flux.value if hasattr(light_curve.flux, "value") else light_curve.flux, dtype=float)
