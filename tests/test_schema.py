import pytest

from vra_fantasy.schema import (
    COMPLETE_COLUMNS,
    EMAIL_COLUMNS,
    MAX_WEEK,
    TeamRecord,
    validate_week,
)


def make_record(**overrides) -> TeamRecord:
    values = {
        "team_name": "Some Team",
        "manager_name": "Jane Doe",
        "league": "Some League",
        "wins": 8,
        "losses": 5,
        "ties": 0,
        "points_for": 1401.52,
        "points_against": 1322.08,
        "point_differential": 79.44,
        "league_rank": 3,
        "streak": "W2",
        "draft_position": 4,
        "draft_grade": "B+",
        "roster_moves": 21,
        "trades": 1,
    }
    values.update(overrides)
    return TeamRecord(**values)


def test_complete_columns_derived_from_model():
    record = make_record()
    assert list(record.model_dump(by_alias=True).keys()) == COMPLETE_COLUMNS
    assert COMPLETE_COLUMNS[0] == "Team Name"
    assert "Ties" in COMPLETE_COLUMNS
    assert "Number of Trades" in COMPLETE_COLUMNS


def test_email_columns_are_subset_of_complete():
    assert set(EMAIL_COLUMNS) <= set(COMPLETE_COLUMNS)


def test_record_dump_uses_output_column_names():
    dump = make_record().model_dump(by_alias=True)
    assert dump["Team Name"] == "Some Team"
    assert dump["Points For"] == 1401.52
    assert dump["Number of Trades"] == 1


def test_optional_draft_fields():
    record = make_record(draft_position=None, draft_grade=None)
    assert record.draft_position is None
    assert record.draft_grade is None


def test_tier2_fields_default_to_absent():
    # FAAB balance especially must default to None (blank cell), never 0:
    # our leagues don't use FAAB
    record = make_record()
    assert record.playoff_seed is None
    assert record.clinched_playoffs is False
    assert record.playoff_games_back is None
    assert record.weekly_roster_adds is None
    assert record.faab_balance is None
    assert record.previous_season_rank is None
    dump = record.model_dump(by_alias=True)
    assert dump["FAAB Balance"] is None
    assert dump["Playoff Seed"] is None


@pytest.mark.parametrize("week", [1, 9, MAX_WEEK])
def test_validate_week_accepts_valid(week):
    assert validate_week(week) == week


@pytest.mark.parametrize("week", [0, MAX_WEEK + 1, -3])
def test_validate_week_rejects_out_of_bounds(week):
    with pytest.raises(ValueError, match="Week must be between"):
        validate_week(week)


@pytest.mark.parametrize("week", ["5", 5.0, None, True])
def test_validate_week_rejects_non_int(week):
    with pytest.raises(ValueError, match="Week must be an integer"):
        validate_week(week)


def test_validate_week_respects_league_max():
    assert validate_week(14, max_week=14) == 14
    with pytest.raises(ValueError, match="between 1 and 14"):
        validate_week(15, max_week=14)
