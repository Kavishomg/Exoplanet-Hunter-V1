# Exoplanet Hunter V1

Analyze TESS and Kepler FITS files for potential exoplanet transits with an interactive web interface.


**Check it out here:** https://exoplanet-hunter-v1.onrender.com/


## About


The goal of this project is not to replace professional astronomy softwares, but to understand how the exoplanet discovery pipeline works by building one from scratch.

Upload a FITS or a Target Pixel File (TPF), and the application automatically extracts the light curve, searches for periodic transit signals, generates diagnostic plots, and produces a structured JSON report.

This project is the first major milestone of my larger Roman Scout project, where I aim to build an end-to-end exoplanet detection pipeline inspired by NASA's Nancy Grace Roman Space Telescope.


## Features


Upload TESS or Kepler FITS/TPF files
Automatic light curve extraction
Normalization, flattening, smoothing and binning
Automatic period search using:
Box Least Squares (BLS)
Lomb–Scargle Periodograms
Candidate detection with confidence scoring
False-positive checks
Seven diagnostic plots generated automatically
JSON analysis report
Interactive browser dashboard built with FastAPI


## Project Structure


app.py

dashboard.html


```planet_hunter/
│ 
├── config.py
├── schemas.py 
├── fits_reader.py 
├── lightcurve.py 
├── periodogram.py 
├── candidates.py 
├── plots.py 
├── reporting.py 
├── io.py 
└── pipeline.py
```


## Analysis Pipeline


Every uploaded file goes through the following stages:


  1. Read FITS file
  2. Extract metadata
  3. Generate target pixel image
  4. Extract light curve
  5. Flatten long-term trends
  6. Bin the data
  7. Smooth noisy observations
  8. Search for periodic signals
  9. Fold the light curve
  10. Detect transit candidates
  11. Generate JSON report
  12. Save diagnostic plots


## Generated Outputs


Each analysis produces:
- Metadata summary
- Candidate classifications
- Confidence scores
- JSON report
- Seven diagnostic plots including:
    - Target Pixel File
    - Raw light curve
    - Flattened light curve
    - Smoothed light curve
    - Periodogram
    - Folded light curve
    - Candidate visualization


## API


| Method | Endpoint | Description |
|:-------|:--------:|------------:|
|GET	 |/|Dashboard|
|GET	 |/health|Backend health chec| 
|POST	 |/api/analyze|Upload a FITS file for analysis|
|GET	 |/outputs/{analysis_id}/...|Download generated plots and reports|


## Configuration


The application can be configured using environment variables.

Some commonly used options include:

- Upload directory
- Output directory
- Maximum upload size
- Allowed CORS origins
- Period search method
- Minimum light curve length
- Automatic output cleanup
- Logging level
- Optional API key authentication


## Technologies Used


### Backend


- Python
- FastAPI
- Uvicorn
- Pydantic


### Astronomy


- Lightkurve
- Astropy


### Scientific Computing


- Numpy
- SciPy
- Matplotlib


### Security


- SlowAPI rate limiting
- Optional API key authentication
- Upload size limits
- Automatic cleanup of old analyses
- Configurable CORS whitelist


## Deployment


The project can be deployed locally or in the cloud.

Supported options include: 

- Docker Compose
- Render
- Railway
- Heroku

The application has been optimised to run with very little memory, making it suitable even for free cloud hosting tiers.


## Repository Structure

```main```

contains the production ready web application

```notebooks``` 

contains the notebooks i used to test and experiment with the scientific libraries.


These notebooks document the experiments and learning process that eventually became the production pipeline.


### Future Plans


This project is only Version 1.

Some planned improvements include: 

- Better false-positive rejection
- Machine learning candidate ranking
- Support for Roman Space Telescope data
- Interactive plot viewer
- Multi-object batch analysis
- GPU acceleration


## Why I Built This


I'm a 17-year-old student who enjoys astronomy, AI and aerospace engineering. Instead of only reading about how exoplanets are discovered, I wanted to understand the process by building my own pipeline.


This project has helped me learn about astronomical data, FITS files, signal processing, transit detection, and software engineering. It's also the foundation for a much larger project that I hope to continue improving over the coming years.


If you have suggestions, ideas, or spot something that could be improved, feel free to open an issue or contribute.

