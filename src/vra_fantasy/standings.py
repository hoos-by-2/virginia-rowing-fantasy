"""Pure transforms from fetched league data to standings DataFrames."""

import logging
from collections.abc import Iterable

import pandas as pd
from yfpy.models import Team

from vra_fantasy.names import TeamNameEntry, resolve_names
from vra_fantasy.schema import COMPLETE_COLUMNS, EMAIL_COLUMNS, TeamRecord
from vra_fantasy.yahoo import LeagueData, decode_name

logger = logging.getLogger(__name__)


def _yahoo_manager_name(team: Team) -> str | None:
    """Extract a manager nickname from a yfpy team, if Yahoo provides one."""
    manager = getattr(team, "manager", None)
    if manager is not None and getattr(manager, "nickname", ""):
        return decode_name(manager.nickname)
    managers = getattr(team, "managers", None) or []
    if isinstance(managers, dict):
        managers = list(managers.values())
    for manager in managers:
        if getattr(manager, "nickname", ""):
            return decode_name(manager.nickname)
    return None


def _streak(team: Team) -> str:
    streak = team.team_standings.streak
    streak_type = decode_name(getattr(streak, "type", "") or "")
    if not streak_type:
        return ""
    return f"{streak_type[0].upper()}{streak.value}"


def team_to_record(
    team: Team, league_name: str, team_names: dict[str, TeamNameEntry]
) -> TeamRecord:
    """Build one validated standings row from a yfpy team."""
    raw_name = decode_name(team.name)
    display_name, manager_name = resolve_names(raw_name, team_names, _yahoo_manager_name(team))
    standings = team.team_standings
    outcomes = standings.outcome_totals
    points_for = float(standings.points_for)
    points_against = float(standings.points_against)
    return TeamRecord(
        team_name=display_name,
        manager_name=manager_name,
        league=league_name,
        wins=outcomes.wins,
        losses=outcomes.losses,
        ties=outcomes.ties,
        points_for=round(points_for, 2),
        points_against=round(points_against, 2),
        point_differential=round(points_for - points_against, 2),
        league_rank=standings.rank,
        streak=_streak(team),
        playoff_seed=getattr(team, "playoff_seed", None),
        clinched_playoffs=bool(getattr(team, "clinched_playoffs", 0) or 0),
        draft_position=team.draft_position,
        draft_grade=decode_name(team.draft_grade) or None,
        roster_moves=team.number_of_moves,
        weekly_roster_adds=getattr(team, "roster_adds_value", None),
        trades=team.number_of_trades,
        # None when the league doesn't use FAAB (ours don't) -> blank output cell
        faab_balance=getattr(team, "faab_balance", None),
        previous_season_rank=getattr(team, "previous_season_team_rank", None),
    )


def _with_playoff_games_back(
    records: list[TeamRecord], num_playoff_teams: int | None
) -> list[TeamRecord]:
    """Fill in each record's games back of the league's last playoff spot.

    Left None when the playoff spot count is unknown; 0.0 for teams at or above
    the cutoff.
    """
    if not num_playoff_teams:
        return records
    cutoff = next((record for record in records if record.league_rank == num_playoff_teams), None)
    if cutoff is None:
        return records

    def games_back(record: TeamRecord) -> float:
        return max(0.0, ((cutoff.wins - record.wins) + (record.losses - cutoff.losses)) / 2)

    return [
        record.model_copy(update={"playoff_games_back": games_back(record)}) for record in records
    ]


def build_standings(
    leagues: Iterable[LeagueData], team_names: dict[str, TeamNameEntry], week: int
) -> pd.DataFrame:
    """Aggregate all leagues into the complete standings DataFrame.

    Sorted by Points For (descending) with a 1-based overall rank index.
    """
    records = []
    for league in leagues:
        if week != league.current_week:
            logger.warning(
                "Requested week (%s) does not match current week (%s) for league %s",
                week,
                league.current_week,
                league.name,
            )
        league_records = [team_to_record(team, league.name, team_names) for team in league.teams]
        league_records = _with_playoff_games_back(league_records, league.num_playoff_teams)
        records.extend(record.model_dump(by_alias=True) for record in league_records)
    standings = pd.DataFrame(records, columns=COMPLETE_COLUMNS)
    standings = standings.sort_values(by="Points For", ascending=False).reset_index(drop=True)
    standings.index += 1
    logger.info("Built standings for %s teams", len(standings))
    return standings


def make_email_standings(complete_standings: pd.DataFrame) -> pd.DataFrame:
    """The abridged standings shared by email: a column subset of the complete table."""
    return complete_standings[EMAIL_COLUMNS].copy()
