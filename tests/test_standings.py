from types import SimpleNamespace

import pytest
from factories import make_league, make_team

from vra_fantasy.names import TeamNameEntry
from vra_fantasy.schema import COMPLETE_COLUMNS, EMAIL_COLUMNS
from vra_fantasy.standings import build_standings, make_email_standings, team_to_record

ENTRIES = {
    "Some Team": TeamNameEntry("Jane Doe"),
    "Other Team": TeamNameEntry("John Smith"),
}


class TestTeamToRecord:
    def test_full_record(self):
        record = team_to_record(make_team(), "League A", ENTRIES)
        assert record.team_name == "Some Team"
        assert record.manager_name == "Jane Doe"
        assert record.league == "League A"
        assert (record.wins, record.losses, record.ties) == (8, 5, 0)
        assert record.points_for == 1401.52
        assert record.points_against == 1322.08
        assert record.point_differential == 79.44
        assert record.league_rank == 3
        assert record.streak == "W2"
        assert record.playoff_seed == 3
        assert record.clinched_playoffs is False
        assert record.playoff_games_back is None
        assert record.draft_position == 4
        assert record.draft_grade == "B+"
        assert record.roster_moves == 21
        assert record.weekly_roster_adds == 2
        assert record.trades == 1
        assert record.faab_balance is None  # our leagues don't use FAAB
        assert record.previous_season_rank == 5

    def test_clinched_playoffs_flag(self):
        record = team_to_record(make_team(clinched_playoffs=1), "L", ENTRIES)
        assert record.clinched_playoffs is True

    def test_faab_balance_kept_when_league_uses_faab(self):
        record = team_to_record(make_team(faab_balance=64), "L", ENTRIES)
        assert record.faab_balance == 64

    def test_byte_names_decoded(self):
        record = team_to_record(make_team(name=b"Some Team"), "League A", ENTRIES)
        assert record.team_name == "Some Team"

    def test_loss_streak(self):
        record = team_to_record(make_team(streak_type="loss", streak_value=3), "L", ENTRIES)
        assert record.streak == "L3"

    def test_missing_streak(self):
        record = team_to_record(make_team(streak_type=""), "L", ENTRIES)
        assert record.streak == ""

    def test_unknown_team_uses_manager_nickname(self, caplog):
        record = team_to_record(make_team(name=b"Unknown", nickname="nick"), "L", ENTRIES)
        assert record.manager_name == "nick"
        assert "not found in team names file" in caplog.text

    def test_manager_fallback_from_managers_list(self):
        team = make_team(
            name=b"Unknown",
            manager=SimpleNamespace(nickname=""),
            managers=[SimpleNamespace(nickname="list_nick")],
        )
        assert team_to_record(team, "L", ENTRIES).manager_name == "list_nick"

    def test_manager_fallback_from_managers_dict(self):
        team = make_team(
            name=b"Unknown",
            manager=SimpleNamespace(nickname=""),
            managers={"1": SimpleNamespace(nickname="dict_nick")},
        )
        assert team_to_record(team, "L", ENTRIES).manager_name == "dict_nick"

    def test_no_manager_found_raises(self):
        team = make_team(name=b"Unknown", manager=SimpleNamespace(nickname=""))
        with pytest.raises(ValueError, match="Manager name not found"):
            team_to_record(team, "L", ENTRIES)


class TestBuildStandings:
    def test_aggregates_and_sorts_by_points_for(self):
        leagues = [
            make_league(
                name="League A",
                teams=[make_team(name=b"Some Team", points_for=1200.0)],
            ),
            make_league(
                name="League B",
                teams=[make_team(name=b"Other Team", points_for=1500.0)],
            ),
        ]
        standings = build_standings(leagues, ENTRIES, week=15)
        assert list(standings.columns) == COMPLETE_COLUMNS
        assert list(standings.index) == [1, 2]
        assert list(standings["Team Name"]) == ["Other Team", "Some Team"]
        assert list(standings["League"]) == ["League B", "League A"]

    def test_week_mismatch_warns(self, caplog):
        leagues = [make_league(current_week=16, teams=[make_team()])]
        build_standings(leagues, ENTRIES, week=15)
        assert "does not match current week (16)" in caplog.text

    def test_matching_week_does_not_warn(self, caplog):
        leagues = [make_league(current_week=15, teams=[make_team()])]
        build_standings(leagues, ENTRIES, week=15)
        assert "does not match" not in caplog.text

    def test_empty_leagues(self):
        standings = build_standings([], ENTRIES, week=15)
        assert standings.empty
        assert list(standings.columns) == COMPLETE_COLUMNS

    def test_playoff_games_back(self):
        # rank 4 is the last playoff spot; rank 5 trails it by 2 games
        teams = [
            make_team(name=b"Some Team", rank=4, wins=8, losses=5, points_for=1200.0),
            make_team(name=b"Other Team", rank=5, wins=6, losses=7, points_for=1100.0),
        ]
        leagues = [make_league(teams=teams, num_playoff_teams=4)]
        standings = build_standings(leagues, ENTRIES, week=15)
        by_team = standings.set_index("Team Name")["Playoff Games Back"]
        assert by_team["Some Team"] == 0.0
        assert by_team["Other Team"] == 2.0

    def test_playoff_games_back_blank_without_playoff_spot_count(self):
        leagues = [make_league(teams=[make_team()], num_playoff_teams=None)]
        standings = build_standings(leagues, ENTRIES, week=15)
        assert standings["Playoff Games Back"].isna().all()


class TestMakeEmailStandings:
    def test_column_subset_preserves_order_and_index(self):
        leagues = [
            make_league(
                teams=[
                    make_team(name=b"Some Team", points_for=1200.0),
                    make_team(name=b"Other Team", points_for=1500.0),
                ]
            )
        ]
        complete = build_standings(leagues, ENTRIES, week=15)
        email = make_email_standings(complete)
        assert list(email.columns) == EMAIL_COLUMNS
        assert list(email.index) == [1, 2]
        assert "Draft Grade" not in email.columns

    def test_returns_copy(self):
        complete = build_standings([make_league(teams=[make_team()])], ENTRIES, week=15)
        email = make_email_standings(complete)
        email.loc[1, "Wins"] = 99
        assert complete.loc[1, "Wins"] == 8
