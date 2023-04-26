import os
import datetime as dt
import json

import requests
from dotenv import load_dotenv


ROOT = os.path.dirname(os.path.abspath(__file__))
CLEAN_DATA_PATH = os.path.join(ROOT, "..", "data", "clean", "co2signal.com")


def main():
    load_dotenv()
    print("query co2signal...")
    if "CO2SIGNAL_API_TOKEN" in os.environ.keys():
        def co2_signal_get_latest(token: str, country_code: str="CA-ON"):
            url = f"https://api.co2signal.com/v1/latest?countryCode={country_code}"
            response = requests.get(url, headers={'auth-token': f'{token}'})
            if response.status_code != 200:
                raise RuntimeError(response.status_code)
            json_string = json.dumps(json.loads(response.content), indent=4)
            print(json_string)
            with open(os.path.join(CLEAN_DATA_PATH, country_code, "latest.json"), "w") as f:
                 f.write(json_string)
 
        co2_signal_get_latest(os.environ["CO2SIGNAL_API_TOKEN"])


if __name__ == "__main__":
    main()
