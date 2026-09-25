from pathlib import Path

import pandas as pd

from vra_fantasy.output import format_awards, format_transactions, write_standings
from vra_fantasy.stats import GradeAward, LeagueMedianCount, Superlative, WeeklyAwards
from vra_fantasy.transactions import FaabBid, LeagueMoves, MostActive, TransactionsSummary

COMPLETE = pd.DataFrame(
    {"Team Name": ["A", "B"], "Wins": [9, 5], "Draft Grade": ["A", "C"]}, index=[1, 2]
)
EMAIL = COMPLETE[["Team Name", "Wins"]]
AWARDS = WeeklyAwards(
    closest_game=Superlative(0.5, "In L, A defeated B 100.0 - 99.5"),
    biggest_blowout=Superlative(50.0, "In L, C defeated D 150.0 - 100.0"),
    top_score=Superlative(150.0, "C (L) scored 150.0"),
    lowest_score=Superlative(99.5, "B (L) scored 99.5"),
    unluckiest_loser=Superlative(99.5, "B (L) lost despite scoring 99.5"),
    luckiest_winner=Superlative(100.0, "A (L) won with only 100.0"),
    overachiever=Superlative(30.0, "C (L) beat their projection by 30.0 (150.0 vs 120.0)"),
    underachiever=Superlative(
        10.0, "D (L) fell short of their projection by 10.0 (100.0 vs 110.0)"
    ),
    upset=Superlative(5.0, "In L, A (projected 100.0) upset B (projected 105.0) 100.0 - 99.5"),
    best_grade=GradeAward(grade="A", teams=("C (L)",)),
    worst_grade=GradeAward(grade="D-", teams=("B (L)", "D (L)")),
    median_score=100.0,
    above_median=(LeagueMedianCount(league="L", above=1, teams=4),),
)
TRANSACTIONS = TransactionsSummary(
    total_moves=5,
    moves_by_league=(LeagueMoves("League A", 3), LeagueMoves("League B", 2)),
    most_active=MostActive(moves=2, teams=("Team One (League A)",)),
    trades=("In League B, X traded P1 to Y for P2",),
    biggest_faab_bid=FaabBid(bid=23, recap="Team Two (League A) bid $23 on Player Two"),
)
NO_FAAB_TRANSACTIONS = TransactionsSummary(
    total_moves=0,
    moves_by_league=(LeagueMoves("League A", 0),),
    most_active=None,
    trades=(),
    biggest_faab_bid=None,
)
MINIMAL_AWARDS = WeeklyAwards(
    closest_game=AWARDS.closest_game,
    biggest_blowout=AWARDS.biggest_blowout,
    top_score=AWARDS.top_score,
    lowest_score=AWARDS.lowest_score,
    unluckiest_loser=None,
    luckiest_winner=None,
    overachiever=None,
    underachiever=None,
    upset=None,
    best_grade=None,
    worst_grade=None,
    median_score=100.0,
    above_median=(),
)


def test_writes_all_files_with_week_in_names(tmp_path: Path):
    written = write_standings(COMPLETE, EMAIL, AWARDS, None, week=15, output_dir=tmp_path)
    assert [path.name for path in written] == [
        "standings_week_15.csv",
        "complete_standings_week_15.csv",
        "weekly_awards_week_15.txt",
    ]
    assert all(path.is_file() for path in written)


def test_creates_missing_output_dir(tmp_path: Path):
    target = tmp_path / "nested" / "output"
    written = write_standings(COMPLETE, EMAIL, None, None, week=3, output_dir=target)
    assert target.is_dir()
    assert [path.name for path in written] == [
        "standings_week_3.csv",
        "complete_standings_week_3.csv",
    ]


def test_csv_round_trip_keeps_rank_index(tmp_path: Path):
    write_standings(COMPLETE, EMAIL, None, None, week=1, output_dir=tmp_path)
    read_back = pd.read_csv(tmp_path / "complete_standings_week_1.csv", index_col=0)
    assert list(read_back.index) == [1, 2]
    assert list(read_back["Team Name"]) == ["A", "B"]


def test_awards_file_content(tmp_path: Path):
    write_standings(COMPLETE, EMAIL, AWARDS, None, week=15, output_dir=tmp_path)
    content = (tmp_path / "weekly_awards_week_15.txt").read_text()
    assert content == format_awards(AWARDS, 15)
    assert "Closest game (0.5 points): In L, A defeated B 100.0 - 99.5" in content
    assert "Biggest blowout (50.0 points): In L, C defeated D 150.0 - 100.0" in content
    assert "Top score: C (L) scored 150.0" in content
    assert "Lowest score: B (L) scored 99.5" in content
    assert "Unluckiest loser: B (L) lost despite scoring 99.5" in content
    assert "Luckiest winner: A (L) won with only 100.0" in content
    assert "Overachiever: C (L) beat their projection by 30.0 (150.0 vs 120.0)" in content
    assert "Upset of the week: In L, A (projected 100.0) upset B (projected 105.0)" in content
    assert "Best report card (A): C (L)" in content
    assert "Worst report card (D-): B (L), D (L)" in content
    assert "All-league median score: 100.0 (teams above: L 1/4)" in content


def test_awards_file_includes_transactions_section(tmp_path: Path):
    write_standings(COMPLETE, EMAIL, AWARDS, TRANSACTIONS, week=15, output_dir=tmp_path)
    content = (tmp_path / "weekly_awards_week_15.txt").read_text()
    assert format_awards(AWARDS, 15) in content
    assert format_transactions(TRANSACTIONS, 15) in content
    assert "Week 15 transactions" in content
    assert "Roster moves: 5 (League A 3, League B 2)" in content
    assert "Most active (2 moves): Team One (League A)" in content
    assert "Trade: In League B, X traded P1 to Y for P2" in content
    assert "Biggest FAAB bid: Team Two (League A) bid $23 on Player Two" in content


def test_transactions_written_without_awards(tmp_path: Path):
    written = write_standings(COMPLETE, EMAIL, None, TRANSACTIONS, week=15, output_dir=tmp_path)
    assert written[-1].name == "weekly_awards_week_15.txt"
    content = written[-1].read_text()
    assert "Week 15 awards" not in content
    assert "Week 15 transactions" in content


def test_faab_line_omitted_without_bids():
    # our leagues don't use FAAB; the ledger must not mention it
    content = format_transactions(NO_FAAB_TRANSACTIONS, 2)
    assert "FAAB" not in content
    assert "Most active" not in content
    assert "Roster moves: 0 (League A 0)" in content


def test_optional_awards_omitted_when_absent():
    content = format_awards(MINIMAL_AWARDS, 2)
    assert "Closest game" in content
    assert "Top score" in content
    assert "Unluckiest loser" not in content
    assert "Luckiest winner" not in content
    assert "Overachiever" not in content
    assert "Underachiever" not in content
    assert "Upset" not in content
    assert "report card" not in content
    assert content.endswith("All-league median score: 100.0\n")
