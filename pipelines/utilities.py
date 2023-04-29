import json
from subprocess import check_call, CalledProcessError

import pandas as pd


def create_json_history_from_git(filepath: str, max_revisions: int=None) -> list:
    """
    Takes ~0.13s/rev.
    """
    i = 1
    data = []
    while True:
        try:
            data.append(get_historical_json_from_git(filepath, i))
            i += 1
        except CalledProcessError:
            break
        if i == max_revisions:
            break
    return data


def get_historical_json_from_git(filepath: str, n_revisions: int) -> dict:
    data = None
    try:
        cmd = ["git", "checkout", f"HEAD~{n_revisions}", filepath]
        print(" ".join(cmd))
        check_call(cmd)
        data = json.loads(open(filepath, "r").read())
    finally:
        # reset the file back to HEAD
        check_call(["git", "checkout", "HEAD", filepath])
    return data


def update_hourly(
        filepath: str,
        hourly_path: str,
        tz: str="America/Toronto",
        dt_column: str="datetime"
) -> pd.DataFrame:
    df_cached = pd.read_csv(hourly_path, index_col=0)
    df_cached.index = pd.to_datetime(df_cached.index)

    i = 1
    data = []
    while True:
        try:
            data.append(get_historical_json_from_git(filepath, i))
            timestamp = pd.to_datetime(pd.json_normalize(data[-1])[dt_column][0])
            i += 1
        except CalledProcessError as e:
            print("CalledProcessError:", e)
            print(f"No more git history for {filepath}")
            break
        if timestamp in df_cached.index:
            print(f"Timestamp {timestamp} already in index")
            break
    if not len(data):
        return None

    df = pd.json_normalize(data)
    df = df.set_index(dt_column)
    df = pd.concat([
        df,
        df_cached
    ], axis=0)
    df.index = pd.to_datetime(df.index, utc=True)
    df = df.tz_convert(tz)
    df = df[[col for col in df.columns if not col.startswith("_")]].drop_duplicates()
    df.to_csv(hourly_path)
    return df
