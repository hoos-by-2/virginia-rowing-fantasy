"""Writing the weekly output files."""

import logging
from pathlib import Path

import pandas as pd

from vra_fantasy.stats import WeeklyAwards
from vra_fantasy.transactions import TransactionsSummary

logger = logging.getLogger(__name__)


def format_awards(awards: WeeklyAwards, week: int) -> str:
    lines = [
        f"Week {week} awards",
        f"Closest game ({awards.closest_game.value} points): {awards.closest_game.recap}",
        f"Biggest blowout ({awards.biggest_blowout.value} points): {awards.biggest_blowout.recap}",
        f"Top score: {awards.top_score.recap}",
        f"Lowest score: {awards.lowest_score.recap}",
    ]
    if awards.unluckiest_loser:
        lines.append(f"Unluckiest loser: {awards.unluckiest_loser.recap}")
    if awards.luckiest_winner:
        lines.append(f"Luckiest winner: {awards.luckiest_winner.recap}")
    if awards.overachiever:
        lines.append(f"Overachiever: {awards.overachiever.recap}")
    if awards.underachiever:
        lines.append(f"Underachiever: {awards.underachiever.recap}")
    if awards.upset:
        lines.append(f"Upset of the week: {awards.upset.recap}")
    if awards.best_grade:
        lines.append(
            f"Best report card ({awards.best_grade.grade}): {', '.join(awards.best_grade.teams)}"
        )
    if awards.worst_grade:
        lines.append(
            f"Worst report card ({awards.worst_grade.grade}): {', '.join(awards.worst_grade.teams)}"
        )
    median_line = f"All-league median score: {awards.median_score}"
    if awards.above_median:
        counts = ", ".join(
            f"{count.league} {count.above}/{count.teams}" for count in awards.above_median
        )
        median_line += f" (teams above: {counts})"
    lines.append(median_line)
    return "\n".join(lines) + "\n"


def format_transactions(transactions: TransactionsSummary, week: int) -> str:
    counts = ", ".join(f"{league.league} {league.moves}" for league in transactions.moves_by_league)
    lines = [
        f"Week {week} transactions",
        f"Roster moves: {transactions.total_moves}" + (f" ({counts})" if counts else ""),
    ]
    if transactions.most_active:
        lines.append(
            f"Most active ({transactions.most_active.moves} moves): "
            f"{', '.join(transactions.most_active.teams)}"
        )
    for trade in transactions.trades:
        lines.append(f"Trade: {trade}")
    if transactions.biggest_faab_bid:
        lines.append(f"Biggest FAAB bid: {transactions.biggest_faab_bid.recap}")
    return "\n".join(lines) + "\n"


def write_standings(
    complete_standings: pd.DataFrame,
    email_standings: pd.DataFrame,
    awards: WeeklyAwards | None,
    transactions: TransactionsSummary | None,
    week: int,
    output_dir: Path,
) -> list[Path]:
    """Write the standings CSVs (and weekly awards recap, if any) to output_dir.

    The awards file also carries the week's transaction ledger when available.
    Creates the output directory if needed; returns the written paths.
    """
    output_dir = Path(output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    email_path = output_dir / f"standings_week_{week}.csv"
    complete_path = output_dir / f"complete_standings_week_{week}.csv"
    email_standings.to_csv(email_path)
    logger.info("Wrote abridged (email) standings to %s", email_path)
    complete_standings.to_csv(complete_path)
    logger.info("Wrote complete standings to %s", complete_path)
    written = [email_path, complete_path]

    sections = []
    if awards is not None:
        sections.append(format_awards(awards, week))
    if transactions is not None:
        sections.append(format_transactions(transactions, week))
    if sections:
        awards_path = output_dir / f"weekly_awards_week_{week}.txt"
        awards_path.write_text("\n".join(sections))
        logger.info("Wrote weekly awards recap to %s", awards_path)
        written.append(awards_path)

    return written
