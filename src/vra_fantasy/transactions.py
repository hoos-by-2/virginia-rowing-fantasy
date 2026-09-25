"""Weekly transaction ledger: waiver activity, trades, and FAAB bids per week.

Tier 2 of STATS_PLAN.md. Yahoo returns the full season's transactions, so each
league's list is filtered to the report week using the scoreboard's matchup
week_start/week_end dates (interpreted in US Eastern time, where NFL waiver
deadlines live). FAAB fields degrade gracefully: our leagues don't use FAAB, so
the bid award only appears when at least one transaction carries a bid.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from vra_fantasy.names import TeamNameEntry, display_team_name
from vra_fantasy.yahoo import LeagueData, decode_name

logger = logging.getLogger(__name__)

EASTERN = ZoneInfo("America/New_York")

# Transaction types counted as roster moves (trades are reported separately).
_MOVE_TYPES = {"add", "drop", "add/drop"}


@dataclass(frozen=True)
class LeagueMoves:
    league: str
    moves: int


@dataclass(frozen=True)
class MostActive:
    """The team(s) with the most roster moves this week."""

    moves: int
    teams: tuple[str, ...]  # "Team (League)" labels


@dataclass(frozen=True)
class FaabBid:
    """The week's biggest FAAB bid; only present in leagues that use FAAB."""

    bid: int
    recap: str


@dataclass(frozen=True)
class TransactionsSummary:
    """The week's transaction ledger across all leagues.

    most_active is None when there were no roster moves; biggest_faab_bid is
    None when no transaction carried a FAAB bid (e.g. waiver-priority leagues).
    """

    total_moves: int
    moves_by_league: tuple[LeagueMoves, ...]
    most_active: MostActive | None
    trades: tuple[str, ...]
    biggest_faab_bid: FaabBid | None


def _week_window(league: LeagueData) -> tuple[int, int] | None:
    """The week's [start, end) timestamp bounds, from the matchup dates."""
    starts = [m for m in (getattr(matchup, "week_start", "") for matchup in league.matchups) if m]
    ends = [m for m in (getattr(matchup, "week_end", "") for matchup in league.matchups) if m]
    if not starts or not ends:
        return None
    start = datetime.strptime(min(starts), "%Y-%m-%d").replace(tzinfo=EASTERN)
    end = datetime.strptime(max(ends), "%Y-%m-%d").replace(tzinfo=EASTERN) + timedelta(days=1)
    return int(start.timestamp()), int(end.timestamp())


def _players(transaction) -> list:
    players = getattr(transaction, "players", None) or []
    if isinstance(players, dict):
        players = list(players.values())
    return players


def _move_team_name(transaction) -> str | None:
    """The Yahoo team name behind an add/drop, from its players' transaction data."""
    for player in _players(transaction):
        data = getattr(player, "transaction_data", None)
        for attribute in ("destination_team_name", "source_team_name"):
            team_name = decode_name(getattr(data, attribute, "") or "")
            if team_name:
                return team_name
    return None


def _player_names(players: list) -> str:
    names = [decode_name(getattr(player, "full_name", "") or "") for player in players]
    return ", ".join(name for name in names if name) or "unnamed players"


def _trade_recap(transaction, league_name: str, team_names: dict[str, TeamNameEntry]) -> str | None:
    trader = decode_name(getattr(transaction, "trader_team_name", "") or "")
    tradee = decode_name(getattr(transaction, "tradee_team_name", "") or "")
    if not trader or not tradee:
        return None
    sent_by_trader = []
    sent_by_tradee = []
    for player in _players(transaction):
        data = getattr(player, "transaction_data", None)
        source = decode_name(getattr(data, "source_team_name", "") or "")
        (sent_by_trader if source == trader else sent_by_tradee).append(player)
    trader_display = display_team_name(trader, team_names)
    tradee_display = display_team_name(tradee, team_names)
    return (
        f"In {league_name}, {trader_display} traded {_player_names(sent_by_trader)} "
        f"to {tradee_display} for {_player_names(sent_by_tradee)}"
    )


def summarize_weekly_transactions(
    leagues: list[LeagueData], team_names: dict[str, TeamNameEntry] | None = None
) -> TransactionsSummary | None:
    """Summarize the report week's transactions across all leagues.

    Returns None when no league has transactions fetched (e.g. fetched with
    include_transactions=False). Leagues whose week window can't be derived
    (no matchups) are skipped with a warning.
    """
    team_names = team_names or {}
    move_counts: dict[tuple[str, str], int] = {}  # (league, team label) -> moves
    league_moves: dict[str, int] = {}
    trades: list[str] = []
    faab_bids: list[FaabBid] = []
    any_fetched = False

    for league in leagues:
        if not league.transactions:
            continue
        any_fetched = True
        window = _week_window(league)
        if window is None:
            logger.warning(
                "No matchup dates to bound the week for league %s; skipping transactions",
                league.name,
            )
            continue
        league_moves.setdefault(league.name, 0)
        for transaction in league.transactions:
            status = decode_name(getattr(transaction, "status", "") or "")
            if status and status != "successful":
                continue
            timestamp = getattr(transaction, "timestamp", None)
            if timestamp is None or not window[0] <= int(timestamp) < window[1]:
                continue
            transaction_type = decode_name(getattr(transaction, "type", "") or "")
            if transaction_type == "trade":
                recap = _trade_recap(transaction, league.name, team_names)
                if recap:
                    trades.append(recap)
                continue
            if transaction_type not in _MOVE_TYPES:
                continue
            league_moves[league.name] += 1
            team_name = _move_team_name(transaction)
            if team_name:
                label = f"{display_team_name(team_name, team_names)} ({league.name})"
                move_counts[(league.name, label)] = move_counts.get((league.name, label), 0) + 1
                bid = getattr(transaction, "faab_bid", None)
                if bid is not None:
                    added = [
                        player
                        for player in _players(transaction)
                        if getattr(getattr(player, "transaction_data", None), "type", "") == "add"
                    ] or _players(transaction)
                    faab_bids.append(
                        FaabBid(bid=int(bid), recap=f"{label} bid ${bid} on {_player_names(added)}")
                    )

    if not any_fetched:
        return None

    most_active = None
    if move_counts:
        top_moves = max(move_counts.values())
        most_active = MostActive(
            moves=top_moves,
            teams=tuple(label for (_, label), moves in move_counts.items() if moves == top_moves),
        )

    return TransactionsSummary(
        total_moves=sum(league_moves.values()),
        moves_by_league=tuple(
            LeagueMoves(league=league, moves=moves) for league, moves in league_moves.items()
        ),
        most_active=most_active,
        trades=tuple(trades),
        biggest_faab_bid=max(faab_bids, key=lambda bid: bid.bid) if faab_bids else None,
    )
