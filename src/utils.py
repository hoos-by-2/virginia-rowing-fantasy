import logging
import numpy as np
import pandas as pd
import os
import yaml
from pathlib import Path
from typing import Dict, Any
from yfpy.query import YahooFantasySportsQuery
logging.getLogger("yfpy.query").setLevel(logging.WARNING)


def read_yaml(file_path: str) -> Dict[str, Any]:
    """
    Reads a YAML file and returns its contents as a dictionary.
    
    :param file_path: Path to the YAML file.
    :return: Dictionary containing the YAML file's contents.
    """
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)
    return data

def get_game_id(league_id="435399"):
    """
    Retrieves all the Yahoo fantasy games and their IDs. The game_id is required to get the standings and changes every year
    :return:
    List of  all Yahoo Fantasy Sports game keys by ID (from year of inception to present), sorted by season/year.
    """
    session = YahooFantasySportsQuery(
            league_id=league_id, 
            game_code="nfl", 
            yahoo_access_token_json={
                "access_token": os.environ["YAHOO_ACCESS_TOKEN"],
                "consumer_key": os.environ["YAHOO_CONSUMER_KEY"],
                "consumer_secret": os.environ["YAHOO_CONSUMER_SECRET"],
                "guid": None,
                "refresh_token": os.environ["YAHOO_REFRESH_TOKEN"],
                "token_time": "token_time",
                "token_type": "bearer"
            }
        )
    
    return session.get_all_yahoo_fantasy_game_keys()


def split_df(df):
    if len(df) % 2 != 0:  # Handling `df` with `odd` number of rows
        df = df.iloc[:-1, :]
    df1, df2 = np.array_split(df, 2)
    return df1, df2


def post_process_standings(df: pd.DataFrame) -> pd.DataFrame:
    if "Points For" in df.columns:
        df["Points For"] = df["Points For"].round(2)
    if "Points Against" in df.columns:
        df["Points Against"] = df["Points Against"].round(2)
    if "Point Differential" in df.columns:
        df["Point Differential"] = df["Point Differential"].round(2)
    if "Team Names" in df.columns:
        df["Team Names"] = df["Team Names"].replace("Alek Blumberg", "Alek Blumberg (fake)")
    return df