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
        check_call(["git", "checkout", f"HEAD~{n_revisions}", filepath])
        data = json.loads(open(filepath, "r").read())
    finally:
        # reset the file back to HEAD
        check_call(["git", "checkout", "HEAD", filepath])
    return data


def update_hourly(filepath: str, hourly_path: str) -> pd.DataFrame:
    df_cached = pd.read_csv(hourly_path, index_col=0)
    df_cached.index = pd.to_datetime(df_cached.index)

    i = 1
    data = []
    while True:
        try:
            data.append(get_historical_json_from_git(filepath, i))
            timestamp = pd.to_datetime(pd.json_normalize(data[-1])["data.datetime"][0])
            i += 1
        except CalledProcessError:
            break
        if timestamp in df_cached.index:
            break
    df = pd.json_normalize(data).drop_duplicates()
    df = df.set_index("data.datetime")
    df = pd.concat([
        df,
        df_cached
    ], axis=0)
    df = df[[col for col in df.columns if not col.startswith("_")]]
    df.to_csv(hourly_path)
    return df
