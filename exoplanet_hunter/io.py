import gzip
import logging
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from .config import Settings

logger = logging.getLogger(__name__)


def new_analysis_id() -> str:
    return uuid4().hex


async def save_upload(file: UploadFile, settings: Settings, analysis_id: str) -> Path:
    settings.ensure_directories()
    suffix = Path(file.filename or "upload.fits").suffix or ".fits"
    target_path = settings.data_dir / f"{analysis_id}{suffix}"

    size = 0
    with target_path.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_bytes:
                target_path.unlink(missing_ok=True)
                raise ValueError(f"Upload exceeds {settings.max_upload_mb} MB limit.")
            output.write(chunk)

    await file.close()
    logger.info("Saved upload %s (%d bytes)", target_path.name, size)

    if target_path.suffix == ".gz":
        fits_path = target_path.with_suffix("")
        try:
            with gzip.open(target_path, "rb") as f_in, fits_path.open("wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
            target_path.unlink()
            logger.info("Decompressed %s -> %s", target_path.name, fits_path.name)
            return fits_path
        except Exception as exc:
            target_path.unlink(missing_ok=True)
            fits_path.unlink(missing_ok=True)
            raise ValueError(f"Failed to decompress .gz file: {exc}") from exc

    return target_path


def cleanup_upload(upload_path: Path) -> None:
    if upload_path.exists():
        try:
            upload_path.unlink()
            logger.info("Cleaned up upload %s", upload_path.name)
        except OSError as exc:
            logger.warning("Failed to clean up upload %s: %s", upload_path.name, exc)


def create_run_dir(settings: Settings, analysis_id: str) -> Path:
    run_dir = settings.output_dir / analysis_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def cleanup_partial_run(run_dir: Path) -> None:
    if run_dir.exists():
        shutil.rmtree(run_dir)
