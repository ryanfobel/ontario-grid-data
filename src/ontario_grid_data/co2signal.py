import os
import datetime as dt
import json
from subprocess import check_call, check_output, CalledProcessError

import pandas as pd
import requests
from dotenv import load_dotenv

from .utilities import update_hourly


ROOT = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_PATH = os.path.join(ROOT, "..", "..", "data", "raw", "co2signal.com")
CLEAN_DATA_PATH = os.path.join(ROOT, "..", "..", "data", "clean", "co2signal.com")


def co2signal_get_latest(token: str, country_code: str="CA-ON") -> dict:
    url = f"https://api.co2signal.com/v1/latest?countryCode={country_code}"
    response = requests.get(url, headers={'auth-token': f'{token}'})
    if response.status_code != 200:
        raise RuntimeError(response.status_code)
    json_string = json.dumps(json.loads(response.content), indent=4)
    print(json_string)
    with open(os.path.join(RAW_DATA_PATH, country_code, "latest", "output.json"), "w") as f:
        f.write(json_string)
    return json.loads(json_string)


def clean_json(json_output: dict) -> dict:
    json_output.pop("_disclaimer")
    json_output.pop("status")
    json_output.pop("countryCode")
    json_output["datetime"] = pd.to_datetime(
        json_output["data"]["datetime"]
    ).tz_convert("America/Toronto").isoformat()
    json_output["data"].pop("datetime")
    return json_output


def main():
    load_dotenv()
    print("query co2signal...")
    if "CO2SIGNAL_API_TOKEN" in os.environ.keys():
        json_output = co2signal_get_latest(os.environ["CO2SIGNAL_API_TOKEN"])
        clean_json(json_output)
        with open(os.path.join(CLEAN_DATA_PATH, "CA-ON", "latest", "output.json"), "w") as f:
            f.write(json.dumps(json_output, indent=4))

        # Commit changes
        check_call(["git", "add", "data"])
        try:
            check_output(['git', 'commit', '-m', 'update data'])
        except CalledProcessError as e:
            if (
                'no changes added to commit' not in e.output.decode("utf-8") and
                'nothing to commit' not in e.output.decode("utf-8")
             ):
                print(e.output)
                raise

    filepath = os.path.abspath(os.path.join(CLEAN_DATA_PATH, "CA-ON", "latest", "output.json"))
    hourly_path = os.path.abspath(os.path.join(CLEAN_DATA_PATH, "CA-ON", "hourly", "output.csv"))
    update_hourly(filepath, hourly_path)


if __name__ == "__main__":
    main()
