import os
import datetime as dt
import json

import pandas as pd

from .CA import fetch_production_by_fuel, fetch_production, fetch_price


ROOT = os.path.dirname(os.path.abspath(__file__))
CLEAN_DATA_PATH = os.path.join(ROOT, "..", "..", "data", "clean", "ieso.ca")


def main():
    TZ = "America/Toronto"
    now = dt.datetime.utcnow()
    production_by_source = fetch_production_by_fuel(target_datetime=now)
    if production_by_source:
        production_by_source[-1]['datetime'] = pd.to_datetime(
            production_by_source[-1]['datetime']
        ).tz_convert(TZ).isoformat()
        with open(os.path.join(CLEAN_DATA_PATH, "latest", "production_by_source.json"), "w") as f:
            f.write(json.dumps(production_by_source[-1], indent=4))

    production_data = fetch_production(target_datetime=now)
    if len(production_data):
        timestamp = production_data["dt"].unique()[-1].tz_convert(TZ)
        production_data = production_data[production_data["dt"] == timestamp]

        plants = {
            "datetime": timestamp.isoformat(),
            "plants": production_data[["name", "fuel"]].set_index("name").to_dict()["fuel"]
        }
        with open(os.path.join(CLEAN_DATA_PATH, "latest", "plants.json"), "w") as f:
            f.write(json.dumps(plants, indent=4))

        production_by_plant = production_data[["name", "production"]].set_index("name").to_dict()["production"]
        output = {
            "datetime": timestamp.isoformat(),
            "production_by_plant": production_by_plant
        }
        with open(os.path.join(CLEAN_DATA_PATH, "latest", "production_by_plant.json"), "w") as f:
            f.write(json.dumps(output, indent=4))

    price = fetch_price(target_datetime=now)
    if price:
        price[-1]['datetime'] = pd.to_datetime(
            price[-1]['datetime']
        ).tz_convert("America/Toronto").isoformat()
        with open(os.path.join(CLEAN_DATA_PATH, "latest", "price.json"), "w") as f:
            f.write(json.dumps(price[-1], indent=4))

if __name__ == "__main__":
    main()