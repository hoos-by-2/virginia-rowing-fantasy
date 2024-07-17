import logging
import numpy as np
from pathlib import Path
from yfpy.query import YahooFantasySportsQuery
logging.getLogger("yfpy.query").setLevel(logging.WARNING)

def get_game_id(league_id="435399"):
    """
    Retrieves all the Yahoo fantasy games and their IDs. The game_id is required to get the standings and changes every year
    :return:
    List of  all Yahoo Fantasy Sports game keys by ID (from year of inception to present), sorted by season/year.
    """
    query = YahooFantasySportsQuery(Path("credentials"), league_id=league_id)
    return query.get_all_yahoo_fantasy_game_keys()


def split_df(df):
    if len(df) % 2 != 0:  # Handling `df` with `odd` number of rows
        df = df.iloc[:-1, :]
    df1, df2 = np.array_split(df, 2)
    return df1, df2