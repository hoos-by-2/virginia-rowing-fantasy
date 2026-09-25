"""Lightweight fakes of yfpy model objects for testing the pure transform layers."""

from datetime import datetime
from types import SimpleNamespace

from vra_fantasy.transactions import EASTERN
from vra_fantasy.yahoo import LeagueData

# Matchup dates used by default across factories; transactions default to a
# timestamp inside this window.
WEEK_START = "2025-12-09"
WEEK_END = "2025-12-15"
MID_WEEK_TIMESTAMP = int(datetime(2025, 12, 11, 12, 0, tzinfo=EASTERN).timestamp())


def make_team(
    name: bytes | str = b"Some Team",
    nickname: str = "yahoo_nick",
    wins: int = 8,
    losses: int = 5,
    ties: int = 0,
    points_for: float = 1401.523,
    points_against: float = 1322.081,
    rank: int = 3,
    streak_type: str = "win",
    streak_value: int = 2,
    playoff_seed: int | None = 3,
    clinched_playoffs: int = 0,
    draft_position: int | None = 4,
    draft_grade: str = "B+",
    number_of_moves: int = 21,
    number_of_trades: int = 1,
    roster_adds_value: int | None = 2,
    faab_balance: int | None = None,  # our leagues don't use FAAB; None is the norm
    previous_season_team_rank: int | None = 5,
    manager: SimpleNamespace | None = None,
    managers: list | dict | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        manager=manager if manager is not None else SimpleNamespace(nickname=nickname),
        managers=managers or [],
        team_standings=SimpleNamespace(
            outcome_totals=SimpleNamespace(wins=wins, losses=losses, ties=ties),
            points_for=points_for,
            points_against=points_against,
            rank=rank,
            streak=SimpleNamespace(type=streak_type, value=streak_value),
        ),
        playoff_seed=playoff_seed,
        clinched_playoffs=clinched_playoffs,
        draft_position=draft_position,
        draft_grade=draft_grade,
        number_of_moves=number_of_moves,
        number_of_trades=number_of_trades,
        roster_adds_value=roster_adds_value,
        faab_balance=faab_balance,
        previous_season_team_rank=previous_season_team_rank,
    )


def make_matchup(
    name_a: bytes | str,
    points_a: float,
    name_b: bytes | str,
    points_b: float,
    projected_a: float | None = None,
    projected_b: float | None = None,
    grade_a: str | None = None,
    grade_b: str | None = None,
    week_start: str = WEEK_START,
    week_end: str = WEEK_END,
) -> SimpleNamespace:
    # yfpy defaults an absent projection to total=0.0 rather than omitting it
    def team(name, points, projected, team_key):
        return SimpleNamespace(
            name=name,
            team_key=team_key,
            team_points=SimpleNamespace(total=points),
            team_projected_points=SimpleNamespace(
                total=projected if projected is not None else 0.0
            ),
        )

    keys = ("399.l.1.t.1", "399.l.1.t.2")
    grades = [
        SimpleNamespace(grade=grade, team_key=key)
        for grade, key in zip((grade_a, grade_b), keys, strict=True)
        if grade is not None
    ]
    return SimpleNamespace(
        teams=[
            team(name_a, points_a, projected_a, keys[0]),
            team(name_b, points_b, projected_b, keys[1]),
        ],
        matchup_grades=grades,
        week_start=week_start,
        week_end=week_end,
        is_tied=int(points_a == points_b),
        matchup_recap_title="",
    )


def make_transaction(
    transaction_type: str = "add",
    team_name: str = "Some Team",
    player_name: str = "Player One",
    timestamp: int = MID_WEEK_TIMESTAMP,
    faab_bid: int | None = None,  # our leagues don't use FAAB; None is the norm
    status: str = "successful",
) -> SimpleNamespace:
    """An add/drop-style transaction attributed to one team."""
    data = SimpleNamespace(
        type="drop" if transaction_type == "drop" else "add",
        destination_team_name="" if transaction_type == "drop" else team_name,
        source_team_name=team_name if transaction_type == "drop" else "",
    )
    return SimpleNamespace(
        type=transaction_type,
        status=status,
        timestamp=timestamp,
        faab_bid=faab_bid,
        players=[SimpleNamespace(full_name=player_name, transaction_data=data)],
        trader_team_name="",
        tradee_team_name="",
    )


def make_trade(
    trader: str = "Some Team",
    tradee: str = "Other Team",
    trader_sends: tuple[str, ...] = ("Player One",),
    tradee_sends: tuple[str, ...] = ("Player Two",),
    timestamp: int = MID_WEEK_TIMESTAMP,
) -> SimpleNamespace:
    def player(name, source, destination):
        return SimpleNamespace(
            full_name=name,
            transaction_data=SimpleNamespace(
                type="trade", source_team_name=source, destination_team_name=destination
            ),
        )

    players = [player(name, trader, tradee) for name in trader_sends]
    players += [player(name, tradee, trader) for name in tradee_sends]
    return SimpleNamespace(
        type="trade",
        status="successful",
        timestamp=timestamp,
        faab_bid=None,
        players=players,
        trader_team_name=trader,
        tradee_team_name=tradee,
    )


def make_league(
    name: str = "League A",
    league_id: str = "111111",
    current_week: int = 15,
    end_week: int = 17,
    teams: list | None = None,
    matchups: list | None = None,
    num_playoff_teams: int | None = None,
    transactions: list | None = None,
) -> LeagueData:
    return LeagueData(
        league_id=league_id,
        name=name,
        current_week=current_week,
        end_week=end_week,
        teams=teams or [],
        matchups=matchups or [],
        num_playoff_teams=num_playoff_teams,
        transactions=transactions or [],
    )
