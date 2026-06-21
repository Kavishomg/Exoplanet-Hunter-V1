import asyncio
import logging
import shutil
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from exoplanet_hunter.config import settings
from exoplanet_hunter.pipeline import AnalysisPipeline
from exoplanet_hunter.schemas import AnalysisResponse

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}. Try again later."},
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_directories()
    asyncio.create_task(_cleanup_loop())
    logger.info("Exoplanet Hunter started (upload_limit=%dMB, ttl=%dh)", settings.max_upload_mb, settings.output_ttl_hours)
    yield
    logger.info("Exoplanet Hunter shutting down")


app = FastAPI(
    title="Exoplanet Hunter V1 Astronomy Engine",
    description="Backend scientific analysis API for uploaded TPF/FITS files.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings.ensure_directories()
app.mount("/outputs", StaticFiles(directory=settings.output_dir), name="outputs")

DASHBOARD_PATH = Path(__file__).parent / "dashboard.html"


@app.get("/", include_in_schema=False)
async def serve_dashboard():
    if DASHBOARD_PATH.exists():
        return FileResponse(DASHBOARD_PATH, media_type="text/html")
    raise HTTPException(status_code=404, detail="Dashboard not found")


@app.get("/health")
@limiter.limit("30/minute")
async def health(request: Request) -> dict:
    output_count = sum(1 for _ in settings.output_dir.iterdir()) if settings.output_dir.exists() else 0
    data_size_mb = sum(f.stat().st_size for f in settings.data_dir.rglob("*") if f.is_file()) / (1024 * 1024) if settings.data_dir.exists() else 0
    return {
        "status": "ok",
        "output_count": output_count,
        "data_dir_size_mb": round(data_size_mb, 2),
        "max_upload_mb": settings.max_upload_mb,
    }


@app.post("/api/analyze", response_model=AnalysisResponse)
@limiter.limit("5/hour")
async def analyze_fits(request: Request, file: UploadFile = File(...)) -> AnalysisResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A FITS/TPF file upload is required.")

    filename = file.filename.lower()
    if not filename.endswith((".fits", ".fit", ".fz", ".tpf")):
        raise HTTPException(status_code=400, detail="Upload must be a FITS/TPF file.")

    if settings.api_key:
        api_key = request.headers.get("X-API-Key", "")
        if api_key != settings.api_key:
            raise HTTPException(status_code=401, detail="Invalid or missing API key.")

    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {settings.max_upload_mb} MB.")

    pipeline = AnalysisPipeline(settings=settings)
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(_run_pipeline, pipeline, file),
            timeout=120.0,
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Analysis timed out after 120 seconds. Try a smaller file.")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Analysis failed for %s", filename)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc


def _run_pipeline(pipeline: AnalysisPipeline, file: UploadFile) -> AnalysisResponse:
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(pipeline.analyze_upload(file))
    finally:
        loop.close()


async def _cleanup_loop():
    while True:
        try:
            await asyncio.sleep(3600)
            _cleanup_old_outputs()
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Cleanup task error")


def _cleanup_old_outputs():
    if not settings.output_dir.exists():
        return
    cutoff = time.time() - (settings.output_ttl_hours * 3600)
    removed = 0
    for entry in settings.output_dir.iterdir():
        if entry.is_dir() and entry.stat().st_mtime < cutoff:
            shutil.rmtree(entry)
            removed += 1
    if removed:
        logger.info("Cleaned up %d expired output directories", removed)
