import os
from pathlib import Path
from yfpy.query import YahooFantasySportsQuery
from src.logger import get_logger

logger = get_logger(__name__)

def get_yahoo_session(league_id: str, game_id: str, credentials_path: str = "credentials") -> YahooFantasySportsQuery:
    """
    Creates the Yahoo Fantasy Sports Query Session for the given league
    :param league_id: League ID
    :param game_id: Game ID (default is GAME_ID)
    :param credentials_path: Path to the credentials file or directory
    :return: Yahoo Fantasy Sports Query Session
    """
    session = None
    logger.info(f"Creating Yahoo session for league {league_id}")
    credentials_path = Path(credentials_path)
    try:
        session = YahooFantasySportsQuery(
            league_id=league_id, 
            game_code="nfl", 
            game_id=game_id,
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
    except Exception as e:
        raise RuntimeError(f"Failed to create Yahoo session for league {league_id}: {e}")
    return session
