from datetime import datetime

from factories import make_league, make_matchup, make_trade, make_transaction

from vra_fantasy.names import TeamNameEntry
from vra_fantasy.transactions import EASTERN, summarize_weekly_transactions

MATCHUPS = [make_matchup(b"A", 100.0, b"B", 90.0)]
OUT_OF_WEEK_TIMESTAMP = int(datetime(2025, 11, 1, tzinfo=EASTERN).timestamp())


class TestSummarizeWeeklyTransactions:
    def test_counts_moves_and_finds_most_active(self):
        leagues = [
            make_league(
                name="League A",
                matchups=MATCHUPS,
                transactions=[
                    make_transaction(team_name="Team One"),
                    make_transaction(transaction_type="add/drop", team_name="Team One"),
                    make_transaction(transaction_type="drop", team_name="Team Two"),
                ],
            ),
            make_league(
                name="League B",
                matchups=MATCHUPS,
                transactions=[make_transaction(team_name="Team Three")],
            ),
        ]
        summary = summarize_weekly_transactions(leagues)
        assert summary.total_moves == 4
        assert {(league.league, league.moves) for league in summary.moves_by_league} == {
            ("League A", 3),
            ("League B", 1),
        }
        assert summary.most_active.moves == 2
        assert summary.most_active.teams == ("Team One (League A)",)

    def test_most_active_collects_ties(self):
        leagues = [
            make_league(
                name="L",
                matchups=MATCHUPS,
                transactions=[
                    make_transaction(team_name="Team One"),
                    make_transaction(team_name="Team Two"),
                ],
            )
        ]
        summary = summarize_weekly_transactions(leagues)
        assert summary.most_active.moves == 1
        assert set(summary.most_active.teams) == {"Team One (L)", "Team Two (L)"}

    def test_filters_to_week_window(self):
        leagues = [
            make_league(
                name="L",
                matchups=MATCHUPS,
                transactions=[
                    make_transaction(team_name="Team One"),
                    make_transaction(team_name="Team One", timestamp=OUT_OF_WEEK_TIMESTAMP),
                ],
            )
        ]
        summary = summarize_weekly_transactions(leagues)
        assert summary.total_moves == 1

    def test_skips_failed_transactions(self):
        leagues = [
            make_league(
                name="L",
                matchups=MATCHUPS,
                transactions=[make_transaction(team_name="Team One", status="failed")],
            )
        ]
        summary = summarize_weekly_transactions(leagues)
        assert summary.total_moves == 0
        assert summary.most_active is None

    def test_trade_recap(self):
        trade = make_trade(
            trader="Some Team",
            tradee="Other Team",
            trader_sends=("Player One", "Player Two"),
            tradee_sends=("Player Three",),
        )
        leagues = [make_league(name="L", matchups=MATCHUPS, transactions=[trade])]
        summary = summarize_weekly_transactions(leagues)
        assert summary.trades == (
            "In L, Some Team traded Player One, Player Two to Other Team for Player Three",
        )
        # trades are not counted as roster moves
        assert summary.total_moves == 0

    def test_trade_uses_display_name_overrides(self):
        entries = {"Some Team": TeamNameEntry("Jane Doe", "Renamed Team")}
        trade = make_trade(trader="Some Team", tradee="Other Team")
        leagues = [make_league(name="L", matchups=MATCHUPS, transactions=[trade])]
        summary = summarize_weekly_transactions(leagues, entries)
        assert summary.trades[0].startswith("In L, Renamed Team traded")

    def test_no_faab_bids_by_default(self):
        # our leagues don't use FAAB: bids come back None and no award is given
        leagues = [make_league(name="L", matchups=MATCHUPS, transactions=[make_transaction()])]
        summary = summarize_weekly_transactions(leagues)
        assert summary.biggest_faab_bid is None

    def test_biggest_faab_bid_when_league_uses_faab(self):
        leagues = [
            make_league(
                name="L",
                matchups=MATCHUPS,
                transactions=[
                    make_transaction(team_name="Team One", player_name="Player One", faab_bid=7),
                    make_transaction(team_name="Team Two", player_name="Player Two", faab_bid=23),
                ],
            )
        ]
        summary = summarize_weekly_transactions(leagues)
        assert summary.biggest_faab_bid.bid == 23
        assert summary.biggest_faab_bid.recap == "Team Two (L) bid $23 on Player Two"

    def test_none_when_no_transactions_fetched(self):
        assert summarize_weekly_transactions([make_league(matchups=MATCHUPS)]) is None
        assert summarize_weekly_transactions([]) is None

    def test_league_without_matchups_skipped_with_warning(self, caplog):
        leagues = [
            make_league(name="L", matchups=[], transactions=[make_transaction()]),
        ]
        summary = summarize_weekly_transactions(leagues)
        assert "No matchup dates to bound the week for league L" in caplog.text
        assert summary.total_moves == 0
        assert summary.moves_by_league == ()
