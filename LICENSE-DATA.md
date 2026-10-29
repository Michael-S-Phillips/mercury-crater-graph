# Data license

The code in this repository (`scripts/` and the explorer page) is released under the MIT License; see `LICENSE`.

The data products are released under the Creative Commons Attribution 4.0 International License (CC BY 4.0), https://creativecommons.org/licenses/by/4.0/. This covers:

- `outputs/` (crater table with graph metrics, edge list, and analysis records)
- `inputs/` files derived in this work (hollow positions and host assignments, completeness grid, northern-plains mask, thermal-model grid, crater floor depths)
- `explorer/data/` and `explorer/tiles/` (the data and basemap tiles behind the interactive explorer)
- `figures/`

Copyright (c) 2026 Michael Phillips.

## Source data

These products derive from published catalogs and mosaics. Anyone who uses them should also cite:

- Herrick, R. R., Bateman, E. M., Crumpacker, W. G., and Bates, D. (2018). Observations from a global database of impact craters on Mercury with diameters greater than 5 km. *Journal of Geophysical Research: Planets*, 123, 2089–2109. https://doi.org/10.1029/2017JE005516 (crater positions, diameters, and attributes)
- Orgel, C., et al. (2020). Re-examination of the population, stratigraphy, and sequence of Mercurian basins. *Journal of Geophysical Research: Planets*, 125, e2019JE006212. https://doi.org/10.1029/2019JE006212 (basins)
- Bickel, V. T., Deutsch, A. N., and Blewett, D. T. (2025). Hollows on Mercury: Creation and analysis of a global reference catalog with deep learning. *Journal of Geophysical Research: Machine Learning and Computation*, 2, e2024JH000431. https://doi.org/10.1029/2024JH000431 (hollow detections, recomputed here with the MESSENGER camera model)
- Denevi, B. W., et al. (2018). Calibration, projection, and final image products of MESSENGER's Mercury Dual Imaging System. *Space Science Reviews*, 214, 2. https://doi.org/10.1007/s11214-017-0440-y (MDIS global mosaics used for the basemap tiles)
