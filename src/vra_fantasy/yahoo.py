"""The only layer that talks to the Yahoo Fantasy Sports API (via yfpy).

Authentication is handled entirely by yfpy: it reads YAHOO_CONSUMER_KEY,
YAHOO_CONSUMER_SECRET, and the Yahoo access token fields from the environment
(or the project .env file), refreshes expired tokens, and persists refreshed
token data back to the .env file so re-authentication is never needed.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from yfpy.models import Game, Matchup, Team, Transaction
from yfpy.query import YahooFantasySportsQuery

from vra_fantasy.names import sanitize_name
from vra_fantasy.schema import GAME_CODE, validate_week

logger = logging.getLogger(__name__)


def decode_name(value: bytes | str) -> str:
    """Normalize yfpy name fields, which are returned as UTF-8 bytes, to str."""
    return value.decode("utf-8") if isinstance(value, bytes) else value


def create_session(
    league_id: str,
    game_id: int | None = None,
    env_file_location: Path | None = None,
) -> YahooFantasySportsQuery:
    """Create an authenticated Yahoo query session for one league.

    :param league_id: League ID to scope the session to.
    :param game_id: Yahoo game ID for the season; None means the current season.
    :param env_file_location: Directory containing the .env file with Yahoo
        credentials; defaults to the current working directory. Refreshed access
        tokens are persisted back to this file.
    """
    logger.info("Creating Yahoo session for league %s", league_id)
    return YahooFantasySportsQuery(
        league_id=league_id,
        game_code=GAME_CODE,
        game_id=game_id,
        env_file_location=env_file_location or Path.cwd(),
        save_token_data_to_env_file=True,
    )


@dataclass(frozen=True)
class LeagueData:
    """Everything fetched from Yahoo for one league, in a single pass."""

    league_id: str
    name: str
    current_week: int
    end_week: int
    teams: list[Team] = field(repr=False)
    matchups: list[Matchup] = field(repr=False)
    # None when league settings were unavailable; playoff columns stay blank
    num_playoff_teams: int | None = None
    transactions: list[Transaction] = field(default_factory=list, repr=False)


def fetch_league_data(
    league_id: str,
    game_id: int,
    week: int,
    include_matchups: bool = True,
    include_transactions: bool = True,
    env_file_location: Path | None = None,
) -> LeagueData:
    """Fetch league metadata, settings, standings teams, week matchups, and
    transactions for one league.

    :param include_matchups: Skip the scoreboard query (used for the weekly
        award stats) when False.
    :param include_transactions: Skip the transactions query (used for the
        weekly transaction ledger) when False.
    """
    session = create_session(league_id, game_id, env_file_location)
    metadata = session.get_league_metadata()
    # league names can carry emoji too; sanitize once here so LeagueData.name
    # is output-ready everywhere (standings League column, recaps, logs)
    name = sanitize_name(decode_name(metadata.name))
    # the league's real season length caps the requested week
    validate_week(week, max_week=int(metadata.end_week))
    logger.info("Fetching data for league %s (%s), week %s", name, league_id, week)
    settings = session.get_league_settings()
    teams = list(session.get_league_standings().teams)
    matchups = (
        list(session.get_league_scoreboard_by_week(week).matchups) if include_matchups else []
    )
    transactions = list(session.get_league_transactions()) if include_transactions else []
    return LeagueData(
        league_id=league_id,
        name=name,
        current_week=int(metadata.current_week),
        end_week=int(metadata.end_week),
        teams=teams,
        matchups=matchups,
        num_playoff_teams=getattr(settings, "num_playoff_teams", None),
        transactions=transactions,
    )


def list_game_keys(league_id: str) -> list[Game]:
    """Retrieve all Yahoo fantasy game keys by season.

    The game_id changes every year; this is how the new one is found for config.yaml.
    """
    session = create_session(league_id)
    return session.get_all_yahoo_fantasy_game_keys()
