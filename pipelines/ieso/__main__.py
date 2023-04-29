import os
import datetime as dt
import json

import pandas as pd

from .CA import fetch_production_by_fuel, fetch_production, fetch_price


ROOT = os.path.dirname(os.path.abspath(__file__))
CLEAN_DATA_PATH = os.path.join(ROOT, "..", "..", "data", "clean", "ieso.ca")


def main():
    now = dt.datetime.utcnow()
    summary_json = fetch_production_by_fuel(target_datetime=now)
    if summary_json:
        summary_json[-1]['datetime'] = pd.to_datetime(
            summary_json[-1]['datetime']
        ).tz_convert("America/Toronto").isoformat()
        summary_path = os.path.join(CLEAN_DATA_PATH, "latest", "summary.json")
        print(summary_path)
        with open(summary_path, "w") as f:
            f.write(json.dumps(summary_json[-1], indent=4))

    data = fetch_production(target_datetime=now)
    if len(data):
        timestamp = data["dt"].unique()[-1]
        data = data[data["dt"] == timestamp]

        plants = data[["name", "fuel"]].set_index("name").to_dict()["fuel"]
        with open(os.path.join(CLEAN_DATA_PATH, "latest", "plants.json"), "w") as f:
            f.write(json.dumps(plants, indent=4))

        output = data[["name", "production"]].set_index("name").to_dict()["production"]
        with open(os.path.join(CLEAN_DATA_PATH, "latest", "output.json"), "w") as f:
            f.write(json.dumps(output, indent=4))

    price_json = fetch_price(target_datetime=now)
    if price_json:
        price_json[-1]['datetime'] = pd.to_datetime(
            price_json[-1]['datetime']
        ).tz_convert("America/Toronto").isoformat()
        price_path = os.path.join(CLEAN_DATA_PATH, "latest", "price.json")
        print(price_path)
        with open(price_path, "w") as f:
            f.write(json.dumps(price_json[-1], indent=4))

if __name__ == "__main__":
    main()