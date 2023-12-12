import os

import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np


ROOT = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_PATH = os.path.join(ROOT, "..", "data", "raw", "oeb.ca")
CLEAN_DATA_PATH = os.path.join(ROOT, "..", "data", "clean", "oeb.ca")
ELECTRICITY_RATES_FILEPATH = os.path.abspath(os.path.join(RAW_DATA_PATH, "historcial-electricity-rates.html"))
GAS_RATES_FILEPATH = os.path.abspath(os.path.join(RAW_DATA_PATH, "historcial-natural-gas-rates.html"))


def make_subs(headers, subs):
    result = headers
    for a, b in subs.items():
        result = [s.replace(a, b).strip() for s in result]
    return result


def get_electricity_rates():
    response = requests.get("https://www.oeb.ca/consumer-information-and-protection/electricity-rates/historical-electricity-rates")
    with open(ELECTRICITY_RATES_FILEPATH, "w") as f:
        f.write(response.content.decode("utf-8"))


def get_gas_rates():
    response = requests.get("https://www.oeb.ca/consumer-information-and-protection/natural-gas-rates/historical-natural-gas-rates")
    with open(GAS_RATES_FILEPATH, "w") as f:
        f.write(response.content.decode("utf-8"))


def convert_table_to_df(table):
    rows = table.find_all(name="tr")
    headers = make_subs(
        [th.text for th in rows[0].find_all("th")],
        subs = {
            "\xa0": " ",
            "\n": "",
            "   ": " ",
            "*": "",
        }
    )

    # pad missing columns
    rows = rows[1:]
    for i, tr in enumerate(rows):
        tds = [td.text for td in tr.find_all(name="td")]
        rows[i] = tds + (len(headers) - len(tds))*['']

    data = {}
    for i, col in enumerate(headers):
        data[col] = make_subs(
            [row[i] for row in rows],
            subs = {
                "*": "",
                ",": "",
            }
        )
    return pd.DataFrame(data)


def convert_electricity_table_to_df(table):
    df = convert_table_to_df(table)
    df = df.set_index("Effective date")
    df.index = pd.to_datetime(df.index)
    for col in df.columns:
        df[col] = (
            df[col].str.replace(" ¢ per kWh", "")
        )
    if "Residential threshold for lower tier price (kWh per month)" in df.columns:
        pat = r"(?P<summer>\S+) \(Summer\)\s+(?P<winter>\S+) \(Winter\)"
        special = df['Residential threshold for lower tier price (kWh per month)'].str.extract(pat).dropna()
        df["Residential threshold for lower tier price (kWh per month) [Summer]"] = df["Residential threshold for lower tier price (kWh per month)"]
        df["Residential threshold for lower tier price (kWh per month) [Winter]"] = df["Residential threshold for lower tier price (kWh per month)"]
        df = df.drop(columns=["Residential threshold for lower tier price (kWh per month)"])
        df.loc[special.index, "Residential threshold for lower tier price (kWh per month) [Summer]"] = special["summer"]
        df.loc[special.index, "Residential threshold for lower tier price (kWh per month) [Winter]"] = special["winter"]
        na_index = df[df["Higher tier price (¢ per kWh)"] == ""].index
        df.loc[na_index, "Residential threshold for lower tier price (kWh per month) [Summer]"] = 0
        df.loc[na_index, "Residential threshold for lower tier price (kWh per month) [Winter]"] = 0
        df.loc[na_index, "Higher tier price (¢ per kWh)"] = df.loc[na_index, "Lower tier price (¢ per kWh)"]

    for col in df.columns:
        df[col] = df[col].astype(float)

    return df


def convert_gas_table_to_df(table):
    df = convert_table_to_df(table)
    df = df.set_index("Date")
    df = df.drop(columns="Detailed rates")
    df.index = pd.to_datetime(df.index, format="%b %Y")

    if "Gas cost adjustment (¢/m³)" in df.columns:
        na_index = df[df["Gas cost adjustment (¢/m³)"] == "-"].index
        df.loc[na_index, "Effective price (¢/m³)"] = df.loc[na_index, "Commodity price (¢/m³)"] 
        df.loc[na_index, "Gas cost adjustment (¢/m³)"] = 0

    # for col in df.columns:
    #     df[col] = df[col].astype(float)

    return df


def main():
    get_electricity_rates()
    try:
        with open(ELECTRICITY_RATES_FILEPATH, "r") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        rate_types = [h2.contents[0] for h2 in soup.find_all(name="h2") if len(h2.contents) > 1]
        tables = soup.find_all(name="table")
        for rate_type, table in zip(rate_types, tables):
            df = convert_electricity_table_to_df(table)
            df.to_csv(os.path.join(CLEAN_DATA_PATH, "electricity", f"{rate_type}.csv"))
    except Exception as e:
        print("Error extracting electricity rates:", e)

    get_gas_rates()
    try:
        with open(GAS_RATES_FILEPATH, "r") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        zones = [h2.contents[0] for h2 in soup.find_all(name="h2") if len(h2.contents) > 1]
        tables = soup.find_all(name="table")
        for zone, table in zip(zones, tables):
            df = convert_gas_table_to_df(table)
            df.to_csv(os.path.join(CLEAN_DATA_PATH, "natural gas", f"{zone}.csv"))
    except Exception as e:
        print("Error extracting natural gas rates:", e)

if __name__ == "__main__":
    main()
