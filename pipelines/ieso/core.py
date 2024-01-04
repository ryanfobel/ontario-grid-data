import os
import glob
import datetime as dt

import requests
import pandas as pd


ROOT = os.path.dirname(os.path.abspath(__file__))
CLEAN_DATA_PATH = os.path.join(ROOT, "..", "..", "data", "clean", "ieso.ca")
RAW_DATA_PATH = os.path.join(ROOT, "..", "..", "data", "raw", "ieso.ca")


def download_url(url, filepath, force=False):
    if not os.path.exists(filepath) or force:
        print(f"Download { filepath }")
        r = requests.get(url)
        if r.ok:
            with open(filepath,'wb') as output_file:
                output_file.write(r.content)
        else:
            raise RuntimeError("Error downloading file")


def get_historical_file_list_pre2019() -> pd.DataFrame:
    years = range(2010, 2020)
    df = pd.DataFrame(
        {
            "year": years,
            "url": [f"https://ieso.ca/-/media/Files/IESO/Power-Data/data-directory/GOC-{ year }.ashx" for year in years]
        }
    )
    df.loc[df.index[-1], "url"] = "https://ieso.ca/-/media/Files/IESO/Power-Data/data-directory/GOC-2019-Jan-April.ashx"
    df["filepath"] = [
        os.path.abspath(os.path.join(RAW_DATA_PATH, os.path.splitext(url.split('/')[-1])[0] + ".xlsx"))
        for url in df["url"]
    ]
    return df


def get_historical_file_list() -> pd.DataFrame:
    tz = dt.timezone(dt.timedelta(hours=-5))
    dates = [
        dt.isoformat() for dt in pd.date_range(
            dt.datetime.strptime("2019-05-01", '%Y-%m-%d').astimezone(tz),
            dt.datetime.now(tz), freq='MS'
        )
    ]
    df = pd.DataFrame({"date": dates})["date"].str.extract("(?P<year>\d{4})-(?P<month>\d{2})-\d{2}")
    df["year"] = df["year"].astype(int)
    df["month"] = df["month"].astype(int)
    df["url"] = [
        f"http://reports.ieso.ca/public/GenOutputCapabilityMonth/PUB_GenOutputCapabilityMonth_{year}{month:02d}.csv"
        for month, year in zip(df["month"], df["year"])
    ]
    df["filepath"] = [
        os.path.abspath(
            os.path.join(
                RAW_DATA_PATH,
                f"PUB_GenOutputCapabilityMonth_{year}{month:02d}.csv"))
                for month, year in zip(df["month"], df["year"])
    ]
    return df


def download_raw_data():
    historical_files_pre2019 = get_historical_file_list_pre2019()

    for year, row in historical_files_pre2019.iterrows():
        try:
            download_url(row["url"], row["filepath"])
        except RuntimeError as e:
            print(e)

    historical_files = get_historical_file_list()

    for index, row in historical_files.iterrows():
        try:
            download_url(row["url"], row["filepath"])
        except RuntimeError as e:
            print(e)

    # Force download of most recent month
    try:
        download_url(row["url"], row["filepath"], force=True)
    except RuntimeError as e:
        print(e)

    return historical_files_pre2019["filepath"].tolist() + historical_files["filepath"].tolist()


def cleanup_monthly_data(df_input: pd.DataFrame, measurement: str="Output") -> pd.DataFrame:
    df = pd.DataFrame()
    output_mask = df_input["Measurement"] == measurement
    columns = ["Generator"] + [f"Hour {x}" for x in range(1,25)]
    for date in df_input["Delivery Date"].unique():
        index = df_input[(df_input["Delivery Date"] == date) & output_mask].index
        df_output = df_input.loc[index, columns].set_index("Generator").T
        df_output.index = pd.to_datetime(
            [f"{date}T{x:02}:00:00" for x in range(24)]
        ).tz_localize(-5*60*60).tz_convert("America/Toronto")
        df = pd.concat([
            df,
            df_output
        ], axis=0)
    return df


def cleanup_yearly_data():
    max_year = max([
        int(os.path.splitext(os.path.basename(file))[0])
        for file in glob.glob(os.path.join(CLEAN_DATA_PATH, "hourly", "output", "*.csv"))
    ])
    historical_files_pre2019 = get_historical_file_list_pre2019()
    historical_files_pre2019 = historical_files_pre2019[
        historical_files_pre2019["year"] > max_year
    ]
    for index, row in historical_files_pre2019.iterrows():
        year = row["year"]
        output_path = os.path.join(CLEAN_DATA_PATH, "hourly", "output", f"{year}.csv")
        if not os.path.exists(output_path):
            print(year)
            url = row["url"]
            filepath = row["filepath"]
            df = pd.read_excel(filepath, engine='openpyxl')
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
            df.index = pd.to_datetime(
                [f'{row["DATE"].date().isoformat()} {int(row["HOUR"]):02}:00:00' for index, row in df.iterrows()]
            ).tz_localize(-5*60*60).tz_convert("America/Toronto")
            df = df.drop(columns=["DATE", "HOUR"])

            # Add TOTAL column if it doesn't exist
            if "TOTAL" not in df.columns:
                df["TOTAL"] = df.sum(axis=1)
            # Put TOTAL first
            df = df[(["TOTAL"] + [col for col in df.columns if col != "TOTAL"])]
            df.to_csv(output_path)
    
    historical_files = get_historical_file_list()
    historical_files = historical_files[
        historical_files["year"] >= max_year
    ]
    for index, row in historical_files.iterrows():
        output_path = os.path.join(CLEAN_DATA_PATH, "hourly", "output", f"{row['year']}.csv")
        if os.path.exists(output_path):
            df = pd.read_csv(output_path, index_col=0, low_memory=False)
            df.index = pd.to_datetime(df.index, utc=True).tz_convert("America/Toronto")
            if len(df) and (row["month"] <= (max(df.index) - pd.Timedelta(days=1)).month):
                continue
        else:
            df = pd.DataFrame()

        try:
            df = pd.concat([
                df,
                cleanup_monthly_data(pd.read_csv(row["filepath"], skiprows=3, index_col=False))
            ], axis=0)
        except FileNotFoundError as e:
            print(f"File {row['filepath']} not found.", str(e))

        df.to_csv(output_path)
