import os

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)


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
    filename = os.path.join("data", "summary.csv")
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
        df = df.append(pd.DataFrame(data, index=[timeOfReading]))
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
        df = df.append(pd.DataFrame(data), ignore_index=True)
    return df


def get_row_from_plant_level_data(driver, timeOfReading, df_plant_level_data, key):
    filename = os.path.join("data", key + ".csv")
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
        df_out = df_out.append(df_row)
        df_out.to_csv(filename)
        return df_row
    return None


def main():
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
            os.path.join("data", "plants.csv"), index=False
        )
    finally:
        driver.close()


if __name__ == "__main__":
    main()
