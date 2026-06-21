from pathlib import Path
from typing import Any

import numpy as np
from astropy.io import fits

from .schemas import Metadata


IMPORTANT_HEADER_KEYS = (
    "MISSION", "TELESCOP", "INSTRUME", "OBJECT", "TICID", "KEPLERID",
    "KIC", "EPIC", "CAMPAIGN", "SECTOR", "RA_OBJ", "DEC_OBJ", "RA",
    "DEC", "CADENCE", "EXPTIME", "TSTART", "TSTOP", "BJDREFI",
    "BJDREFF", "TIMESYS",
)


def extract_metadata(path: Path) -> Metadata:
    with fits.open(path, memmap=True) as hdul:
        merged: dict[str, Any] = dict(hdul[0].header)
        for hdu in hdul[1:]:
            merged.update({key: value for key, value in hdu.header.items() if key not in merged})

    target_id = _first_present(merged, ("TICID", "KEPLERID", "KIC", "EPIC"))
    raw_header = {key: _json_safe(merged.get(key)) for key in IMPORTANT_HEADER_KEYS if key in merged}

    return Metadata(
        filename=path.name,
        target_id=str(target_id) if target_id is not None else None,
        mission=_as_str(_first_present(merged, ("MISSION", "TELESCOP"))),
        telescope=_as_str(merged.get("TELESCOP")),
        instrument=_as_str(merged.get("INSTRUME")),
        object_name=_as_str(merged.get("OBJECT")),
        ra_deg=_as_float(_first_present(merged, ("RA_OBJ", "RA"))),
        dec_deg=_as_float(_first_present(merged, ("DEC_OBJ", "DEC"))),
        cadence=_as_str(merged.get("CADENCE")),
        exposure_time_seconds=_as_float(merged.get("EXPTIME")),
        time_reference=_format_time_reference(merged),
        observation_start=_as_str(merged.get("TSTART")),
        observation_end=_as_str(merged.get("TSTOP")),
        raw_header=raw_header,
    )


def extract_target_pixel_image(path: Path) -> np.ndarray | None:
    with fits.open(path, memmap=True) as hdul:
        for hdu in hdul:
            data = hdu.data
            if data is None:
                continue
            if isinstance(data, np.ndarray) and data.ndim == 2 and np.isfinite(data).any():
                return np.array(data, dtype=float, copy=True)
            if hasattr(data, "names") and data.names:
                for column in ("FLUX", "SAP_FLUX", "PDCSAP_FLUX"):
                    if column in data.names:
                        flux = np.array(data[column], dtype=float, copy=True)
                        if flux.ndim == 3:
                            return np.nanmedian(flux, axis=0)
                        if flux.ndim == 2:
                            return flux
    return None


def _first_present(header: dict[str, Any], keys: tuple[str, ...]) -> Any | None:
    for key in keys:
        value = header.get(key)
        if value not in (None, ""):
            return value
    return None


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def _as_str(value: Any) -> str | None:
    return None if value in (None, "") else str(value)


def _json_safe(value: Any) -> Any:
    return value if isinstance(value, (str, int, float, bool)) or value is None else str(value)


def _format_time_reference(header: dict[str, Any]) -> str | None:
    system = _as_str(header.get("TIMESYS"))
    refi = _as_float(header.get("BJDREFI"))
    reff = _as_float(header.get("BJDREFF"))
    if refi is None and reff is None:
        return system
    return f"{system or 'TIME'} + {(refi or 0.0) + (reff or 0.0):g}"
