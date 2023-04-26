import os
from typing import List
import json

import datetime as dt
import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)
from dotenv import load_dotenv
import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_PATH = os.path.join(ROOT, "..", "data", "raw", "gridwatch.ca")
CLEAN_DATA_PATH = os.path.join(ROOT, "..", "data", "clean", "gridwatch.ca", "historical")


def convert_index_to_datetime(df: pd.DataFrame) -> pd.DataFrame:
    df.index = pd.to_datetime(df.index)
    return df


def load_file(filename: str, stage: str="clean", source: str="github"):
    if source == "github":
        historical = ""
        if stage=="clean":
            historical = "historical/"
        filepath = f"https://github.com/ryanfobel/gridwatch-history/blob/main/data/{stage}/gridwatch.ca/{historical}{filename}?raw=true"
    else:
        if stage=="clean":
            filepath = os.path.join(CLEAN_DATA_PATH, filename)
        else:
            filepath = os.path.join(RAW_DATA_PATH, filename)
    df = pd.read_csv(filepath, index_col=0, thousands=',')
    if filename in ["summary.csv", "output.csv", "capability.csv"]:
        df = convert_index_to_datetime(df)
    return df


def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    dt_index = extract_datetime_from_string_list(df.index)
    df = df.reset_index().loc[dt_index.index]
    df.index = dt_index.values
    df = df.drop(columns="index")
    return df


def clean_summary(df: pd.DataFrame) -> pd.DataFrame:
    df = clean_df(df)

    percentage_cols = [col for col in df.columns if col.endswith('Percentage')]
    for col in df[percentage_cols]:
        df[col] = df[col].str.replace("%", "").astype(float)
    df = df.rename(columns={col: f"{col.replace('Percentage', '')} (%)" for col in percentage_cols})
    
    output_cols = [col for col in df.columns if col.endswith('Output')]
    mw_cols = output_cols + ["imports", "exports", "netImportExports", "POWER GENERATED"]
    for col in df[mw_cols]:
        df[col] = df[col].str.replace(" MW", "")
        df[col] = df[col].str.replace(",", "").astype(float)
    df = df.rename(columns={col: f"{col.replace('Output', '')} (MW)" for col in output_cols})

    df['TOTAL EMISSIONS'] = df['TOTAL EMISSIONS'].str.replace(" tonnes", "")
    df['TOTAL EMISSIONS'] = df['TOTAL EMISSIONS'].str.replace(",", "").astype(float)
    df['ONTARIO DEMAND'] = df['ONTARIO DEMAND'].str.replace(" MW", "")
    df['ONTARIO DEMAND'] = df['ONTARIO DEMAND'].str.replace(",", "").astype(float)
    df['CO2e INTENSITY'] = df['CO2e INTENSITY'].str.replace(" g/kWh", "").astype(float)

    df = df.rename(columns={
        "imports": "Imports (MW)",
        "exports": "Exports (MW)",
        "netImportExports": "Net Import/Exports (MW)",
        "POWER GENERATED": "Power Generated (MW)",
        "ONTARIO DEMAND": "Ontario Demand (MW)",
        "TOTAL EMISSIONS": "Total Emissions (tonnes)",
        "CO2e INTENSITY": "CO2e Intensity (g/kWh)",
    })
    return df


def extract_datetime_from_string_list(str_list: List[str]) -> pd.Series:
    # Example of the string index: 'Thu Oct 14, 8 AM - 9 AM'
    df = pd.Series(str_list).str.extract(
        r'(?P<dow>[a-zA-Z]{3}) '
        r'(?P<month>[a-zA-Z]{3}) '
        r'(?P<day>\d+), '
        r'(?P<start_hour>\d+) '
        r'(?P<start_AMPM>[A-Z]{2}) - '
        r'(?P<end_hour>\d+) '
        r'(?P<end_AMPM>[A-Z]{2})'
    )
    # convert types
    df = df.dropna()
    df["start_hour"] = df["start_hour"].astype(int)
    df["end_hour"] = df["end_hour"].astype(int)

    # Convert 3-letter month into number
    months = list(set(df["month"].values))
    month_letters_to_number = dict(zip(months, [dt.datetime.strptime(mon, '%b').month for mon in months]))
    df["month"] = df["month"].map(month_letters_to_number)

    df = df.drop(columns=["dow"]).dropna().copy()

    # Find the indices where the months and years "rollover"
    month_rollover_index = df[:-1][
        df.loc[df.index[1:], "month"].values !=
        df.loc[df.index[:-1], "month"].values
    ].index

    year_rollover_index = df.loc[month_rollover_index[:-1]][
        df.loc[month_rollover_index[1:], "month"].values <
        df.loc[month_rollover_index[:-1], "month"].values
    ].index

    # Assume the most recent date is from the current year
    end_year = dt.datetime.now().year
    df["year"] = end_year

    for index in reversed(year_rollover_index):
        df.loc[:index, "year"] = df.loc[:index, "year"] - 1

    # Convert to 24hr time
    start_hour_lt_12_and_PM_index = df[(df["start_hour"] < 12) & (df["start_AMPM"] == "PM")].index
    df.loc[start_hour_lt_12_and_PM_index, "start_hour"] = df.loc[start_hour_lt_12_and_PM_index, "start_hour"] + 12
    start_hour_12_and_AM_index = df[(df["start_hour"] == 12) & (df["start_AMPM"] == "AM")].index
    df.loc[start_hour_12_and_AM_index, "start_hour"] = 0

    # Drop extra columns
    df = df.drop(columns={"end_AMPM", "start_AMPM", "end_hour"})
    df = df.rename(columns={"start_hour": "hour"})
    df["dt"] = pd.to_datetime(df)

    hr_23_index = df[df["hour"] == 23].index
    df.loc[hr_23_index, "dt"] = df.loc[hr_23_index, "dt"] - pd.Timedelta(1, "d")

    return df["dt"]


#############################################################################################
# Selenium code for scraping data from gridwatch.ca
#############################################################################################

def init_driver(headless=False):
    options = webdriver.firefox.options.Options()
    if headless:
        options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
    return webdriver.Firefox(options=options)


def load_page(driver):
    driver.get("https://live.gridwatch.ca/home-page.html")

    timeOfReading = "updating data..."

    # Wait for the page to load
    while timeOfReading == "updating data...":
        timeOfReading = driver.find_element_by_xpath(
            f'//span[@bind="timeOfReading"]/parent::div'
        ).text

    print(f"timeOfReading={ timeOfReading }")
    return timeOfReading


def scrape_summary_data(driver, timeOfReading):
    filename = os.path.join(RAW_DATA_PATH, "summary.csv")
    if os.path.exists(filename):
        df = pd.read_csv(filename, index_col=0)
        if timeOfReading in df.index:
            print("no new data")
            return
    else:
        df = pd.DataFrame()

    data = {}
    for key in ["imports", "exports", "netImportExports"]:
        data[key] = driver.find_element_by_xpath(
            f'//span[@bind="{ key }"]/parent::div'
        ).text

    for key in [
        "POWER GENERATED",
        "ONTARIO DEMAND",
        "TOTAL EMISSIONS",
        "CO2e INTENSITY",
    ]:
        data[key] = driver.find_element_by_xpath(
            f"//p[contains(text(), '{ key }')]/parent::div/following-sibling::div"
        ).text

    for metric in ["Percentage", "Output"]:
        for source in ["nuclear", "hydro", "gas", "wind", "biofuel", "solar"]:
            data[source + metric] = driver.find_element_by_xpath(
                f'//span[@bind="{ source + metric }"]/parent::div'
            ).text

    if timeOfReading not in df.index:
        df = pd.concat(
            [df, pd.DataFrame(data, index=[timeOfReading])],
        )
        df.to_csv(filename)


def scrape_plant_level_data(driver):
    df = pd.DataFrame()
    for source in driver.find_elements_by_xpath('//td[@class="energy-source-title"]'):
        source.click()

        data = {}
        for key in ["name", "output", "capability"]:
            data[key] = [
                e.text
                for e in driver.find_elements_by_xpath(
                    f'//td[@class="power-plant-{ key }-data"]'
                )[2:]
                if e.text
            ]
        data["source"] = [source.text] * len(data[key])
        df = pd.concat(
            [df, pd.DataFrame(data)],
            ignore_index=True
        )
    return df


def get_row_from_plant_level_data(driver, timeOfReading, df_plant_level_data, key):
    filename = os.path.join(RAW_DATA_PATH, key + ".csv")
    if os.path.exists(filename):
        df_out = pd.read_csv(filename, index_col=0)
    else:
        df_out = pd.DataFrame()

    if timeOfReading not in df_out.index:
        df_row = pd.DataFrame(
            {
                k: v
                for k, v in zip(
                    df_plant_level_data["name"].values,
                    df_plant_level_data[key].values,
                )
            },
            index=[timeOfReading],
        )
        df_out = pd.concat(
            [df_out, df_row]
        )
        df_out.to_csv(filename)
        return df_row
    return None


def write_latest_json(name: str):
    history_path = f"{name}.csv"
    latest_path = os.path.join("data", "clean", "gridwatch.ca", "latest", f"{name}.json")
    df = load_file(history_path, source="local")
    df.index = [index.isoformat() for index in df.index]
    df.index.name = "datetime"
    with open(latest_path, "w") as f:
        f.write(json.dumps(df.reset_index().iloc[-1].to_dict(), indent=4))


def main():
    load_dotenv()

    driver = init_driver(headless=True)
    try:
        timeOfReading = load_page(driver)
        scrape_summary_data(driver, timeOfReading)
        df_plant_level_data = scrape_plant_level_data(driver)
        get_row_from_plant_level_data(
            driver, timeOfReading, df_plant_level_data, "output"
        )
        get_row_from_plant_level_data(
            driver, timeOfReading, df_plant_level_data, "capability"
        )
        df_plant_level_data.drop(["output", "capability"], axis=1).to_csv(
            os.path.join(RAW_DATA_PATH, "plants.csv"), index=False
        )
    finally:
        driver.close()

    # Clean data
    print("clean data...")
    clean_summary(
        pd.read_csv(
            os.path.join(RAW_DATA_PATH, "summary.csv"),
            index_col=0,
            thousands=','
        )
    ).to_csv(
        os.path.join(CLEAN_DATA_PATH, "summary.csv")
    )
    for file in ["output.csv", "capability.csv"]:
        clean_df(
            pd.read_csv(
                os.path.join(RAW_DATA_PATH, file),
                index_col=0,
                thousands=','
            )
        ).to_csv(
            os.path.join(CLEAN_DATA_PATH, file)
        )

    print("write latest json files...")
    for name in ["summary", "output", "capability"]:
        write_latest_json(name)

    data_json = fetch_production(target_datetime=now)
    data_json[-1]['datetime'] = data_json[-1]['datetime'].isoformat()
    print(json.dumps(data_json[-1], indent=4))

if __name__ == "__main__":
    main()
