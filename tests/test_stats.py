from factories import make_league, make_matchup

from vra_fantasy.names import TeamNameEntry
from vra_fantasy.stats import compute_weekly_awards


class TestExtremeGames:
    def test_single_matchup_is_both_extremes(self):
        leagues = [make_league(name="League A", matchups=[make_matchup(b"A", 100.0, b"B", 90.0)])]
        awards = compute_weekly_awards(leagues)
        assert awards.closest_game.value == 10.0
        assert awards.biggest_blowout.value == 10.0
        assert awards.closest_game.recap == "In League A, A defeated B 100.0 - 90.0"
        assert awards.closest_game.recap == awards.biggest_blowout.recap

    def test_across_multiple_leagues(self):
        leagues = [
            make_league(
                name="League A",
                matchups=[
                    make_matchup(b"A1", 100.0, b"A2", 99.5),
                    make_matchup(b"A3", 120.0, b"A4", 80.0),
                ],
            ),
            make_league(
                name="League B",
                matchups=[make_matchup(b"B1", 150.25, b"B2", 60.0)],
            ),
        ]
        awards = compute_weekly_awards(leagues)
        assert awards.closest_game.value == 0.5
        assert awards.closest_game.recap == "In League A, A1 defeated A2 100.0 - 99.5"
        assert awards.biggest_blowout.value == 90.25
        assert awards.biggest_blowout.recap == "In League B, B1 defeated B2 150.25 - 60.0"

    def test_tie_recap(self):
        leagues = [make_league(name="League A", matchups=[make_matchup(b"A", 100.0, b"B", 100.0)])]
        awards = compute_weekly_awards(leagues)
        assert awards.closest_game.value == 0.0
        assert awards.closest_game.recap == "In League A, A tied B at 100.0"

    def test_lower_scoring_team_listed_first_still_ordered_by_winner(self):
        leagues = [make_league(name="L", matchups=[make_matchup(b"Loser", 80.0, b"Winner", 95.0)])]
        awards = compute_weekly_awards(leagues)
        assert awards.biggest_blowout.recap == "In L, Winner defeated Loser 95.0 - 80.0"

    def test_display_name_overrides_applied(self):
        entries = {"Ugly 🚀 Name": TeamNameEntry("John Smith", "Pretty Name")}
        leagues = [
            make_league(
                name="L",
                matchups=[
                    make_matchup("Ugly 🚀 Name".encode(), 100.0, "Emoji 🐍 Team".encode(), 90.0)
                ],
            )
        ]
        awards = compute_weekly_awards(leagues, entries)
        assert awards.biggest_blowout.recap == "In L, Pretty Name defeated Emoji Team 100.0 - 90.0"

    def test_no_matchups_returns_none(self):
        assert compute_weekly_awards([make_league(matchups=[])]) is None
        assert compute_weekly_awards([]) is None

    def test_skips_malformed_matchup(self, caplog):
        bad = make_matchup(b"A", 100.0, b"B", 90.0)
        bad.teams.pop()
        good = make_matchup(b"C", 100.0, b"D", 95.0)
        leagues = [make_league(name="L", matchups=[bad, good])]
        awards = compute_weekly_awards(leagues)
        assert "Skipping matchup with 1 teams" in caplog.text
        assert awards.closest_game.recap == "In L, C defeated D 100.0 - 95.0"


class TestScoreAwards:
    def test_top_and_lowest_score_across_leagues(self):
        leagues = [
            make_league(name="League A", matchups=[make_matchup(b"A1", 100.0, b"A2", 55.5)]),
            make_league(name="League B", matchups=[make_matchup(b"B1", 150.25, b"B2", 60.0)]),
        ]
        awards = compute_weekly_awards(leagues)
        assert awards.top_score.value == 150.25
        assert awards.top_score.recap == "B1 (League B) scored 150.25"
        assert awards.lowest_score.value == 55.5
        assert awards.lowest_score.recap == "A2 (League A) scored 55.5"

    def test_luck_awards(self):
        leagues = [
            make_league(
                name="L",
                matchups=[
                    # high-scoring loser and low-scoring winner in different games
                    make_matchup(b"A", 140.0, b"B", 141.0),
                    make_matchup(b"C", 82.0, b"D", 70.0),
                ],
            )
        ]
        awards = compute_weekly_awards(leagues)
        assert awards.unluckiest_loser.value == 140.0
        assert awards.unluckiest_loser.recap == "A (L) lost despite scoring 140.0"
        assert awards.luckiest_winner.value == 82.0
        assert awards.luckiest_winner.recap == "C (L) won with only 82.0"

    def test_luck_awards_none_when_all_tied(self):
        leagues = [make_league(name="L", matchups=[make_matchup(b"A", 100.0, b"B", 100.0)])]
        awards = compute_weekly_awards(leagues)
        assert awards.unluckiest_loser is None
        assert awards.luckiest_winner is None


class TestProjectionAwards:
    def test_overachiever_underachiever_and_upset(self):
        leagues = [
            make_league(
                name="L",
                matchups=[
                    # A beats projection by 20.5; B (projected to win by 15) loses
                    make_matchup(b"A", 120.5, b"B", 95.0, projected_a=100.0, projected_b=115.0),
                    # C falls short by 30
                    make_matchup(b"C", 70.0, b"D", 90.0, projected_a=100.0, projected_b=85.0),
                ],
            )
        ]
        awards = compute_weekly_awards(leagues)
        assert awards.overachiever.value == 20.5
        assert awards.overachiever.recap == "A (L) beat their projection by 20.5 (120.5 vs 100.0)"
        assert awards.underachiever.value == 30.0
        assert (
            awards.underachiever.recap
            == "C (L) fell short of their projection by 30.0 (70.0 vs 100.0)"
        )
        assert awards.upset.value == 15.0
        assert awards.upset.recap == (
            "In L, A (projected 100.0) upset B (projected 115.0) 120.5 - 95.0"
        )

    def test_projection_awards_none_without_projections(self):
        leagues = [make_league(name="L", matchups=[make_matchup(b"A", 100.0, b"B", 90.0)])]
        awards = compute_weekly_awards(leagues)
        assert awards.overachiever is None
        assert awards.underachiever is None
        assert awards.upset is None

    def test_no_upset_when_favorite_wins(self):
        leagues = [
            make_league(
                name="L",
                matchups=[
                    make_matchup(b"A", 110.0, b"B", 90.0, projected_a=105.0, projected_b=95.0)
                ],
            )
        ]
        awards = compute_weekly_awards(leagues)
        assert awards.upset is None

    def test_overachiever_none_when_everyone_underperforms(self):
        leagues = [
            make_league(
                name="L",
                matchups=[
                    make_matchup(b"A", 90.0, b"B", 80.0, projected_a=100.0, projected_b=95.0)
                ],
            )
        ]
        awards = compute_weekly_awards(leagues)
        assert awards.overachiever is None
        assert awards.underachiever.value == 15.0


class TestGradeAwards:
    def test_best_and_worst_grades_collect_ties(self):
        leagues = [
            make_league(
                name="League A",
                matchups=[make_matchup(b"A1", 100.0, b"A2", 90.0, grade_a="A-", grade_b="F")],
            ),
            make_league(
                name="League B",
                matchups=[make_matchup(b"B1", 95.0, b"B2", 85.0, grade_a="A-", grade_b="B+")],
            ),
        ]
        awards = compute_weekly_awards(leagues)
        assert awards.best_grade.grade == "A-"
        assert awards.best_grade.teams == ("A1 (League A)", "B1 (League B)")
        assert awards.worst_grade.grade == "F"
        assert awards.worst_grade.teams == ("A2 (League A)",)

    def test_grade_ordering_respects_modifiers(self):
        leagues = [
            make_league(
                name="L",
                matchups=[
                    make_matchup(b"A", 100.0, b"B", 90.0, grade_a="B+", grade_b="B-"),
                    make_matchup(b"C", 95.0, b"D", 85.0, grade_a="B", grade_b="B"),
                ],
            )
        ]
        awards = compute_weekly_awards(leagues)
        assert awards.best_grade.grade == "B+"
        assert awards.worst_grade.grade == "B-"

    def test_grade_awards_none_without_grades(self):
        leagues = [make_league(name="L", matchups=[make_matchup(b"A", 100.0, b"B", 90.0)])]
        awards = compute_weekly_awards(leagues)
        assert awards.best_grade is None
        assert awards.worst_grade is None

    def test_unparseable_grade_skipped(self):
        leagues = [
            make_league(
                name="L",
                matchups=[make_matchup(b"A", 100.0, b"B", 90.0, grade_a="?", grade_b="C")],
            )
        ]
        awards = compute_weekly_awards(leagues)
        assert awards.best_grade.grade == "C"
        assert awards.worst_grade.grade == "C"


class TestMedianContext:
    def test_median_and_above_median_counts(self):
        leagues = [
            make_league(name="League A", matchups=[make_matchup(b"A1", 100.0, b"A2", 90.0)]),
            make_league(name="League B", matchups=[make_matchup(b"B1", 120.0, b"B2", 80.0)]),
        ]
        awards = compute_weekly_awards(leagues)
        assert awards.median_score == 95.0
        counts = {count.league: (count.above, count.teams) for count in awards.above_median}
        assert counts == {"League A": (1, 2), "League B": (1, 2)}
