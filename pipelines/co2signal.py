import os
import datetime as dt
import json
from subprocess import check_call, CalledProcessError

import requests
from dotenv import load_dotenv

from .utilities import update_hourly


ROOT = os.path.dirname(os.path.abspath(__file__))
CLEAN_DATA_PATH = os.path.join(ROOT, "..", "data", "clean", "co2signal.com")


def co2signal_get_latest(token: str, country_code: str="CA-ON") -> dict:
    url = f"https://api.co2signal.com/v1/latest?countryCode={country_code}"
    response = requests.get(url, headers={'auth-token': f'{token}'})
    if response.status_code != 200:
        raise RuntimeError(response.status_code)
    json_string = json.dumps(json.loads(response.content), indent=4)
    print(json_string)
    with open(os.path.join(CLEAN_DATA_PATH, country_code, "latest.json"), "w") as f:
        f.write(json_string)
    return json.loads(json_string)


def main():
    load_dotenv()
    print("query co2signal...")
    if "CO2SIGNAL_API_TOKEN" in os.environ.keys():
        co2signal_get_latest(os.environ["CO2SIGNAL_API_TOKEN"])
        # Commit changes
        check_call(["git", "add", "data"])
        check_call(["git", "commit", "-m" "\"update data\""])

    filepath = os.path.abspath(os.path.join(CLEAN_DATA_PATH, "CA-ON", "latest.json"))
    hourly_path = os.path.abspath(os.path.join(CLEAN_DATA_PATH, "CA-ON", "hourly.csv"))
    update_hourly(filepath, hourly_path)


if __name__ == "__main__":
    main()
