"""Console entry points: fantasy-standings and fantasy-game-id."""

import argparse
import logging
import sys
from pathlib import Path

from vra_fantasy.config import Config, load_config
from vra_fantasy.names import load_team_names
from vra_fantasy.output import format_awards, format_transactions, write_standings
from vra_fantasy.schema import MAX_WEEK, MIN_WEEK, validate_week
from vra_fantasy.standings import build_standings, make_email_standings
from vra_fantasy.stats import compute_weekly_awards
from vra_fantasy.transactions import summarize_weekly_transactions
from vra_fantasy.yahoo import fetch_league_data, list_game_keys

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )
    logging.getLogger("yfpy.query").setLevel(logging.WARNING)


def _resolve_week(week: int | None) -> int:
    """Validate the --week flag, or prompt for a week when the flag is omitted."""
    if week is not None:
        return validate_week(week)
    while True:
        try:
            raw = input(f"Week number ({MIN_WEEK}-{MAX_WEEK}): ").strip()
        except EOFError:
            raise ValueError(
                "No week provided (pass --week when running non-interactively)"
            ) from None
        try:
            return validate_week(int(raw))
        except ValueError as error:
            print(error if str(error) else f"Invalid week: {raw!r}")


def run_standings(config: Config, week: int, output_dir: Path, include_awards: bool) -> None:
    """Fetch all leagues, build the standings, and write the output files."""
    team_names = load_team_names(config.team_names_path)
    leagues = [
        fetch_league_data(
            league_id,
            config.game_id,
            week,
            include_matchups=include_awards,
            # the transaction ledger needs the matchup dates to bound the week
            include_transactions=include_awards,
        )
        for league_id in config.league_ids
    ]
    complete_standings = build_standings(leagues, team_names, week)
    email_standings = make_email_standings(complete_standings)
    awards = compute_weekly_awards(leagues, team_names) if include_awards else None
    transactions = summarize_weekly_transactions(leagues, team_names) if include_awards else None
    written = write_standings(
        complete_standings, email_standings, awards, transactions, week, output_dir
    )

    print(f"\nWeek {week} standings for {len(leagues)} leagues, {len(complete_standings)} teams.")
    print("Files written:")
    for path in written:
        print(f"  {path}")
    if awards is not None:
        print()
        print(format_awards(awards, week))
    if transactions is not None:
        print(format_transactions(transactions, week))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="fantasy-standings",
        description="Aggregate weekly Yahoo fantasy football standings across all leagues.",
    )
    parser.add_argument(
        "--week",
        type=int,
        help=f"week number ({MIN_WEEK}-{MAX_WEEK}); prompted for when omitted",
    )
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--output-dir", type=Path, help="override the config output_dir")
    parser.add_argument(
        "--no-awards",
        action="store_true",
        help="skip the weekly awards (closest game, blowout, ...) and transaction ledger",
    )
    args = parser.parse_args()

    _setup_logging()
    try:
        config = load_config(args.config)
        week = _resolve_week(args.week)
        output_dir = args.output_dir if args.output_dir is not None else config.output_dir
        run_standings(config, week, output_dir, include_awards=not args.no_awards)
    except (ValueError, FileNotFoundError) as error:
        sys.exit(str(error))


def game_id_main() -> None:
    parser = argparse.ArgumentParser(
        prog="fantasy-game-id",
        description=(
            "List Yahoo fantasy game IDs by season; the game_id in config.yaml "
            "must be updated to the new season's ID every year."
        ),
    )
    parser.add_argument(
        "--league-id",
        help="league ID to authenticate the query with (default: first league in config)",
    )
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    args = parser.parse_args()

    _setup_logging()
    try:
        league_id = args.league_id or load_config(args.config).league_ids[0]
        games = list_game_keys(league_id)
    except (ValueError, FileNotFoundError) as error:
        sys.exit(str(error))
    for game in games:
        print(f"{game.season}: {game.game_id} ({game.code})")
