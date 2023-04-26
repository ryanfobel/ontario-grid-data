import os
import datetime as dt
import json

from .CA import fetch_production


ROOT = os.path.dirname(os.path.abspath(__file__))
CLEAN_DATA_PATH = os.path.join(ROOT, "..", "..", "data", "clean", "ieso.ca")


def main():
    now = dt.datetime.utcnow()
    data_json = fetch_production(target_datetime=now)
    data_json[-1]['datetime'] = data_json[-1]['datetime'].isoformat()
    output_path = os.path.join(CLEAN_DATA_PATH, "latest", "output.json")
    print(output_path)
    with open(output_path, "w") as f:
        f.write(json.dumps(data_json[-1], indent=4))


if __name__ == "__main__":
    main()