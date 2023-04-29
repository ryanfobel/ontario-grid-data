import os
import datetime as dt

import requests
import pandas as pd


ROOT = os.path.dirname(os.path.abspath(__file__))
CLEAN_DATA_PATH = os.path.join(ROOT, "..", "..", "data", "clean", "ieso.ca")
RAW_DATA_PATH = os.path.join(ROOT, "..", "..", "data", "raw", "ieso.ca")


def download_url(url, ext='.xlsx', force=False):
    filename = os.path.join(RAW_DATA_PATH, os.path.splitext(url.split('/')[-1])[0] + ext)
    if not os.path.exists(filename) or force:
        print(f"Download { filename }")
        r = requests.get(url)
        if r.ok:

            with open(filename,'wb') as output_file:
                output_file.write(r.content)
        else:
            raise RuntimeError("Error downloading file")


def get_historical_file_list_pre2019():
    years = range(2010, 2020)
    df = pd.DataFrame(
        {
            "url": [f"https://ieso.ca/-/media/Files/IESO/Power-Data/data-directory/GOC-{ year }.ashx" for year in years]
        },
        index=years
    )
    df.loc[2019, "url"] = 'https://ieso.ca/-/media/Files/IESO/Power-Data/data-directory/GOC-2019-Jan-April.ashx'
    df["ext"] = ".xlsx"
    df["year"] = df.index.astype(str)
    df["filepath"] = [os.path.abspath(p) for p in
        os.path.join(CLEAN_DATA_PATH, "hourly", "output") +
        df["year"] + ".csv"
    ]
    return df


def get_historical_file_list() -> pd.DataFrame:
    dates = [dt.isoformat() for dt in pd.date_range("2019-05-01", dt.datetime.now(), freq='MS')]
    df = pd.DataFrame({"date": dates})["date"].str.extract("(?P<year>\d{4})-(?P<month>\d{2})-\d{2}")
    df["filepath"] = (
        os.path.join(RAW_DATA_PATH, "PUB_GenOutputCapabilityMonth_") +
        df["year"] + df["month"] + ".csv"
    )
    df["filename"] = [os.path.basename(fn) for fn in df["filepath"]]
    df["url"] = (
        "http://reports.ieso.ca/public/GenOutputCapabilityMonth/PUB_GenOutputCapabilityMonth_" +
        df["year"] + df["month"] + ".csv"
    )
    return df


def download_raw_data_pre2019():
    historical_files = get_historical_file_list_pre2019()

    for year, row in historical_files.iterrows():
        download_url(row["url"])

        output_path = os.path.join(CLEAN_DATA_PATH, "hourly", "output", f"{year}.csv")
        if not os.path.exists(output_path):
            print(year)
            url = row["url"]
            filename = os.path.join(RAW_DATA_PATH, os.path.splitext(url.split('/')[-1])[0] + row["ext"])
            df = pd.read_excel(filename, engine='openpyxl')
            drop_columns = {
                2010: "Unnamed: 2",
                2011: "Unnamed: 2",
                2012: "a",
            }
            if year in drop_columns.keys():
                df = df.drop(columns=[drop_columns[year]])
            if "Hour" in df.columns:
                df = df.rename(columns={"Hour": "HOUR"})
            if "Date" in df.columns:
                df = df.rename(columns={"Date": "DATE"})

            df = df[pd.notna(df["DATE"])]
            df["HOUR"] = df["HOUR"] - 1
            df.index = pd.to_datetime([f'{row["DATE"].date().isoformat()} {int(row["HOUR"]):02}:00:00' for index, row in df.iterrows()])
            df = df.drop(columns=["DATE", "HOUR"])

            # Add TOTAL column if it doesn't exist
            if "TOTAL" not in df.columns:
                df["TOTAL"] = df.sum(axis=1)
            # Put TOTAL first
            df = df[(["TOTAL"] + [col for col in df.columns if col != "TOTAL"])]

            df.to_csv(output_path)
    
    return [os.path.abspath(p) for p in historical_files["filepath"]]


def download_raw_data():
    historical_files = get_historical_file_list()

    for index, row in historical_files.iterrows():
        download_url(row["url"], ext=".csv")

    # Force download of most recent month
    download_url(row["url"], ext=".csv", force=True)

    return [os.path.abspath(p) for p in historical_files["filepath"]]


def cleanup_monthly_data(df_input: pd.DataFrame, measurement: str="Output") -> pd.DataFrame:
    df = pd.DataFrame()
    output_mask = df_input["Measurement"] == measurement
    columns = ["Generator"] + [f"Hour {x}" for x in range(1,25)]
    for date in df_input["Delivery Date"].unique():
        index = df_input[(df_input["Delivery Date"] == date) & output_mask].index
        df_output = df_input.loc[index, columns].set_index("Generator").T
        df_output.index = pd.to_datetime([f"{date}T{x:02}:00:00" for x in range(24)])
        df = pd.concat([
            df,
            df_output
        ], axis=0)
    return df


def cleanup_yearly_data():
    historical_files = get_historical_file_list()
    yearly_data = {}
    for index, row in historical_files.iterrows():
        print(row["year"], row["month"])
        if row["year"] not in yearly_data.keys():
            yearly_data[row["year"]] = pd.DataFrame()
        
        yearly_data[row["year"]] = pd.concat([
            yearly_data[row["year"]],
            cleanup_monthly_data(pd.read_csv(row["filepath"], skiprows=3, index_col=False))
        ], axis=0)

    for year, df in yearly_data.items():
        df.to_csv(os.path.join(CLEAN_DATA_PATH, "hourly", "output", f"{year}.csv"))

    return yearly_data
