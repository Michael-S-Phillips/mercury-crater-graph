# Inputs

Everything `scripts/crater_dag.py` and the test scripts read. The derived files come from the analysis of hollows on Mercury by M. S. Phillips (manuscript in preparation), whose code and data are archived separately.

| File | Contents | Source |
|---|---|---|
| `herrick2018_craters_with_hosts.csv` | 31,571 craters ≥ 5 km (position, diameter, catalog attributes) with mean annual surface temperature and a flag for craters assigned at least one hollow | Herrick et al. (2018); host flag and temperature from this work |
| `orgel2020_basins.csv` | Basin centers, diameters, and confidence | Orgel et al. (2020) |
| `crater_floor_depths.csv` | Rim, floor, and rim-to-floor depth (m) of craters ≥ 10 km | USGS 665 m/pixel global DEM (Becker et al., 2016); this work |
| `hollows.csv` | 6,731 hollows: position, field, number of detections, equivalent diameter, stage flag of the source catalog, host crater, and distance from the host center in host radii (`rho`) | Bickel et al. (2025), recomputed with the MESSENGER camera model and merged; host assignment from this work |
| `completeness_1km_10ppd.npz` | Probability that MESSENGER imaging detects a hollow 1 km across, per 0.1° cell (`C1`, rows from 90°N, columns from 0°E) | This work |
| `northern_plains_mask_10ppd.npz` | Northern smooth plains mask on the same grid (`mask`) | This work, from the lineaments of Klimczak et al. (2025) |
| `thermal_grid.npz` | Mean annual surface temperature from a one-dimensional thermal model with the 3:2 resonance, 5° grid (`scripts/thermal.py`) | This work |
