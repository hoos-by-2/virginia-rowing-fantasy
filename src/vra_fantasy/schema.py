"""Output schema contracts: the standings row model and the column lists derived from it."""

from pydantic import BaseModel, ConfigDict, Field

GAME_CODE = "nfl"

MIN_WEEK = 1
# Fallback upper bound; the effective bound is checked against league metadata
# (end_week) at runtime, since Yahoo season length can change.
MAX_WEEK = 18


class TeamRecord(BaseModel):
    """One team's row in the standings output.

    Field order defines the column order of the output CSVs, and serialization
    aliases are the column names: build output rows with model_dump(by_alias=True).
    """

    model_config = ConfigDict(frozen=True)

    team_name: str = Field(serialization_alias="Team Name")
    manager_name: str = Field(serialization_alias="Name")
    league: str = Field(serialization_alias="League")
    wins: int = Field(serialization_alias="Wins")
    losses: int = Field(serialization_alias="Losses")
    ties: int = Field(serialization_alias="Ties")
    points_for: float = Field(serialization_alias="Points For")
    points_against: float = Field(serialization_alias="Points Against")
    point_differential: float = Field(serialization_alias="Point Differential")
    league_rank: int = Field(serialization_alias="League Rank")
    streak: str = Field(serialization_alias="Streak")
    playoff_seed: int | None = Field(default=None, serialization_alias="Playoff Seed")
    clinched_playoffs: bool = Field(default=False, serialization_alias="Clinched Playoffs")
    # None until the league's playoff spot count is known; 0.0 for teams in position
    playoff_games_back: float | None = Field(default=None, serialization_alias="Playoff Games Back")
    draft_position: int | None = Field(default=None, serialization_alias="Draft Position")
    draft_grade: str | None = Field(default=None, serialization_alias="Draft Grade")
    roster_moves: int = Field(default=0, serialization_alias="Roster Moves")
    weekly_roster_adds: int | None = Field(default=None, serialization_alias="Weekly Roster Adds")
    trades: int = Field(default=0, serialization_alias="Number of Trades")
    # None in leagues that don't use FAAB (ours don't) — must stay a blank cell, not 0
    faab_balance: int | None = Field(default=None, serialization_alias="FAAB Balance")
    previous_season_rank: int | None = Field(
        default=None, serialization_alias="Previous Season Rank"
    )


COMPLETE_COLUMNS: list[str] = [
    field.serialization_alias for field in TeamRecord.model_fields.values()
]

EMAIL_COLUMNS: list[str] = [
    "Team Name",
    "Name",
    "League",
    "Wins",
    "Losses",
    "Points For",
    "Points Against",
]

_unknown_email_columns = set(EMAIL_COLUMNS) - set(COMPLETE_COLUMNS)
if _unknown_email_columns:
    raise ValueError(
        f"EMAIL_COLUMNS entries not defined on TeamRecord: {sorted(_unknown_email_columns)}"
    )


def validate_week(week: int, max_week: int = MAX_WEEK) -> int:
    """Validate a week number against the season bounds and return it."""
    if not isinstance(week, int) or isinstance(week, bool):
        raise ValueError(f"Week must be an integer, got {week!r}")
    if not MIN_WEEK <= week <= max_week:
        raise ValueError(f"Week must be between {MIN_WEEK} and {max_week}, got {week}")
    return week
