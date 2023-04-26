import os
import datetime as dt
import json

from .CA import fetch_production, fetch_price


ROOT = os.path.dirname(os.path.abspath(__file__))
CLEAN_DATA_PATH = os.path.join(ROOT, "..", "..", "data", "clean", "ieso.ca")


def main():
    now = dt.datetime.utcnow()
    output_json = fetch_production(target_datetime=now)
    if output_json:
        output_json[-1]['datetime'] = output_json[-1]['datetime'].isoformat()
        output_path = os.path.join(CLEAN_DATA_PATH, "latest", "output.json")
        print(output_path)
        with open(output_path, "w") as f:
            f.write(json.dumps(output_json[-1], indent=4))

    price_json = fetch_price(target_datetime=now)
    if price_json:
        price_json[-1]['datetime'] = price_json[-1]['datetime'].isoformat()
        price_path = os.path.join(CLEAN_DATA_PATH, "latest", "price.json")
        print(price_path)
        with open(price_path, "w") as f:
            f.write(json.dumps(price_json[-1], indent=4))

if __name__ == "__main__":
    main()