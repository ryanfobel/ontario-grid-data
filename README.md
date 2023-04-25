[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/ryanfobel/gridwatch-history/main)

# Gridwatch history

This package downloads hourly data on the Ontario electricity grid from https://gridwatch.ca/ (available as `.csv` files in the [data](https://github.com/ryanfobel/gridwatch-history/blob/main/data/) directory). This provides insight into how Ontario's power generation mix changes over time (e.g., how much power is provided by nuclear, hydro, wind, solar, biofuel and natural gas) and can be used to estimate the CO<sub>2</sub> intensity (i.e., the amount of CO<sub>2</sub> emissions generated per kWh of electricity) as a function of time. If you have access to [hourly electricity use](https://github.com/ryanfobel/utility-bill-scraper) (e.g., provided by many utilities), you can use this data to get a more accurate estimate of your carbon footprint and can measure the impact of shifting electricity use to times when the grid is "cleaner" (e.g., when it is primarily powered by zero-emission sources).

![CO2 intensity](images/ontario_co2_intensity.svg)
![Power generation by source](images/ontario_power_generation_by_source.svg)

## Contributors

Ryan Fobel ([@ryanfobel](https://github.com/ryanfobel))


