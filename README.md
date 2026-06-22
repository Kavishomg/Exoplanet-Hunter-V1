# Exoplanet Hunter V1

A web app that finds potential exoplanets in telescope data. Upload a FITS file, get transit candidates, diagnostic plots, and a full analysis report.

**[Try it live](https://exoplanet-hunter-v1.onrender.com/)** — upload any TESS or Kepler FITS file and see results in seconds.

> ⚠️ **Note:** Hosted on a free tier, so the first request might take ~50s while the server wakes up. After that, it is fast.

---

## Quick Start

### Option 1: Run Locally

```bash
git clone [https://github.com/Kavishomg/Exoplanet-Hunter-V1.git](https://github.com/Kavishomg/Exoplanet-Hunter-V1.git)
cd Exoplanet-Hunter-V1
pip install -r requirements.txt
uvicorn app:app --reload

```

Open `http://localhost:8000` in your browser. Upload a FITS file. Done.

### Option 2: Docker

```bash
git clone [https://github.com/Kavishomg/Exoplanet-Hunter-V1.git](https://github.com/Kavishomg/Exoplanet-Hunter-V1.git)
cd Exoplanet-Hunter-V1
docker compose up

```

Same thing — opens at `http://localhost:8000`.

### Option 3: Just Use the Live Version

No install needed. Go to [exoplanet-hunter-v1.onrender.com](https://exoplanet-hunter-v1.onrender.com/), drop a FITS file, and get your results.

---

## How It Works

1. **Upload:** You upload a FITS or Target Pixel File (TPF) from TESS or Kepler.
2. **Read:** The app reads the file and pulls out the light curve (brightness over time).
3. **Process:** It flattens, bins, and smooths the data to reduce background noise.
4. **Search:** Runs period search algorithms (BLS and Lomb-Scargle) to find repeating dips.
5. **Rank:** Ranks candidates by confidence score and flags possible false positives.
6. **Generate:** Generates 7 diagnostic plots + a structured JSON report.

All of this happens automatically. You just upload and wait.

---

## What You Get

After analysis, you receive:

* **7 diagnostic plots** — Target pixel image, raw/flattened/binned/smoothed light curves, periodogram, and folded light curve.
* **Candidate list** — Ranked by confidence score with period, depth, duration, SNR, and transit count.
* **False positive flags** — Flags like *"only one event observed"*, *"odd/even depth mismatch"*, or *"very deep signal"*.
* **JSON report** — Structured data you can use for further downstream analysis.

---

## Where to Get FITS Files

You need FITS files to use the app. Here's where to find them:

* **[MAST](https://mast.stsci.edu/)** — Mikulski Archive for Space Telescopes. Search by TIC ID or Kepler ID, download TPF or light curve files.
* **[Lightkurve tutorials](https://docs.lightkurve.org/)** — Comes with example FITS files you can download and test with.
* **[TESS](https://tess.mit.edu/)** — TESS mission data. Good for bright stars with potential transits.

*Tip: Just search for a star (like "WASP-18" or "HD 209458"), download the FITS file, and upload it.*

---

## Tech Stack

| Layer | Technologies Used |
| --- | --- |
| **Backend** | Python, FastAPI, Uvicorn |
| **Astronomy** | Lightkurve, Astropy |
| **Math & Data** | NumPy, SciPy, Matplotlib |
| **Frontend** | Vanilla HTML / CSS / JS |
| **Security** | SlowAPI rate limiting, CORS, upload size limits |

---

## Configuration

All settings are controlled through environment variables. No code changes needed.

| Variable | Default | What it does |
| --- | --- | --- |
| `EXOHUNTER_DATA_DIR` | `data/uploads` | Where uploaded files go |
| `EXOHUNTER_OUTPUT_DIR` | `outputs` | Where results are saved |
| `EXOHUNTER_MAX_UPLOAD_MB` | `50` | Max upload file size |
| `EXOHUNTER_ALLOWED_ORIGINS` | `["http://localhost:8000"]` | CORS whitelist |
| `EXOHUNTER_PERIODOGRAM_METHOD` | `auto` | `bls`, `lomb_scargle`, or `auto` |
| `EXOHUNTER_MINIMUM_POINTS` | `50` | Min data points needed |
| `EXOHUNTER_OUTPUT_TTL_HOURS` | `168` | Auto-delete results after N hours |
| `EXOHUNTER_LOG_LEVEL` | `INFO` | Logging verbosity |
| `EXOHUNTER_API_KEY` | *(empty)* | Optional API key auth |

Copy `.env.example` to `.env` and edit if you want to change anything.

---

## Project Structure

```text
exoplanet-hunter-v1/
├── app.py                  # FastAPI server, routes, rate limiting
├── dashboard.html          # Frontend UI
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container build
├── docker-compose.yml      # One-command deploy
├── Procfile                # Render/Railway/Heroku configuration
├── .env.example            # Config template
└── exoplanet_hunter/       # Core package
    ├── config.py           # Settings from env vars
    ├── schemas.py          # Pydantic models
    ├── fits_reader.py      # FITS metadata extraction
    ├── lightcurve.py       # Light curve processing
    ├── periodogram.py      # BLS + Lomb-Scargle search
    ├── candidates.py       # Scoring + false positive flags
    ├── plots.py            # Matplotlib plot generation
    ├── reporting.py        # JSON report output
    ├── io.py               # File handling + cleanup
    └── pipeline.py         # Main analysis orchestrator

```

---

## Deployment

Works on any platform that runs Python. Tested on:

* **Render** — Free tier, 512MB RAM. Uses ~37MB peak. [Deploy guide](https://render.com/docs)
* **Railway** — Similar to Render, uses Procfile.
* **Heroku** — Same Procfile works.
* **Docker** — Works anywhere Docker runs.

**Memory Optimization:** Uses memory-mapped FITS reading, aggressive garbage collection, and scaled periodogram grids to stay under 50MB even for large files.

---

## Branches

* **`main`** — Production app, ready to deploy.
* **`notebooks`** — Experimental Jupyter notebooks used while building the pipeline. Not needed to run the app.

---

## What I Learned

Built this as a 17-year-old who wanted to understand exoplanet detection instead of just reading about it. Turns out building a transit pipeline from scratch teaches you a lot about signal processing, astronomical data formats, and why finding planets is hard.

This is version 1. Plans for future iterations:

* Better false positive rejection
* ML-based candidate ranking
* Support for Roman Space Telescope data
* Interactive plot viewer
* Batch analysis mode

---

## Contributing

Got ideas or found a bug? Open an issue. Want to help? Fork it, make changes, and open a PR.

This is a learning project — contributions from other students are especially welcome!



