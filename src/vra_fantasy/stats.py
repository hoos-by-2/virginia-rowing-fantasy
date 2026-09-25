"""Weekly award stats computed across all leagues' matchups.

Tier 1 of STATS_PLAN.md: every award here derives from the scoreboard data the
pipeline already fetches — no extra API calls. Awards that depend on data Yahoo
may not provide (projections, matchup grades) are None when it is absent.
"""

import logging
import statistics
from dataclasses import dataclass

from vra_fantasy.names import TeamNameEntry, display_team_name
from vra_fantasy.yahoo import LeagueData, decode_name

logger = logging.getLogger(__name__)

# Yahoo matchup grades run A+ (best) to F- (worst).
_GRADE_LETTERS = "ABCDEF"
_GRADE_MODIFIERS = {"+": 0, "": 1, "-": 2}


@dataclass(frozen=True)
class Superlative:
    """One award: the deciding value and a human-readable recap."""

    value: float
    recap: str


@dataclass(frozen=True)
class GradeAward:
    """The teams sharing the week's best (or worst) Yahoo matchup grade."""

    grade: str
    teams: tuple[str, ...]


@dataclass(frozen=True)
class LeagueMedianCount:
    """How many of a league's teams scored above the all-league median."""

    league: str
    above: int
    teams: int


@dataclass(frozen=True)
class WeeklyAwards:
    """All weekly awards across every league.

    The luck awards are None when every matchup tied; the projection awards
    are None when Yahoo projections are unavailable (or nobody beat/missed
    their projection); the grade awards are None when Yahoo matchup grades
    are unavailable.
    """

    closest_game: Superlative
    biggest_blowout: Superlative
    top_score: Superlative
    lowest_score: Superlative
    unluckiest_loser: Superlative | None
    luckiest_winner: Superlative | None
    overachiever: Superlative | None
    underachiever: Superlative | None
    upset: Superlative | None
    best_grade: GradeAward | None
    worst_grade: GradeAward | None
    median_score: float
    above_median: tuple[LeagueMedianCount, ...]


@dataclass(frozen=True)
class _TeamGame:
    """One team's week: its side of a matchup, flattened for ranking."""

    league: str
    label: str  # "Team (League)"
    points: float
    projected: float | None
    result: str  # "win", "loss", or "tie"


def _recap(league_name: str, names: list[str], points: list[float]) -> str:
    (name_a, name_b), (points_a, points_b) = names, points
    if points_a == points_b:
        return f"In {league_name}, {name_a} tied {name_b} at {points_a}"
    if points_a < points_b:
        name_a, name_b = name_b, name_a
        points_a, points_b = points_b, points_a
    return f"In {league_name}, {name_a} defeated {name_b} {points_a} - {points_b}"


def _projected_points(team) -> float | None:
    """A team's Yahoo projection, or None when absent (yfpy defaults it to 0)."""
    projected = getattr(team, "team_projected_points", None)
    total = getattr(projected, "total", None)
    try:
        value = float(total)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _grade_key(grade: str) -> tuple[int, int] | None:
    """Sort key for a Yahoo letter grade (lower is better), or None if unparseable."""
    if not grade:
        return None
    letter, modifier = grade[0], grade[1:]
    if letter not in _GRADE_LETTERS or modifier not in _GRADE_MODIFIERS:
        return None
    return (_GRADE_LETTERS.index(letter), _GRADE_MODIFIERS[modifier])


def _grade_awards(
    grades: list[tuple[tuple[int, int], str, str]],
) -> tuple[GradeAward | None, GradeAward | None]:
    if not grades:
        return None, None

    def award(target_key: tuple[int, int]) -> GradeAward:
        grade = next(grade for key, grade, _ in grades if key == target_key)
        teams = tuple(label for key, _, label in grades if key == target_key)
        return GradeAward(grade=grade, teams=teams)

    keys = [key for key, _, _ in grades]
    return award(min(keys)), award(max(keys))


def compute_weekly_awards(
    leagues: list[LeagueData], team_names: dict[str, TeamNameEntry] | None = None
) -> WeeklyAwards | None:
    """Compute all weekly awards across all leagues' matchups.

    Returns None when no matchups are present (e.g. fetched with
    include_matchups=False).
    """
    team_names = team_names or {}
    games: list[_TeamGame] = []
    matchup_recaps: list[tuple[float, str]] = []  # (point diff, recap)
    upsets: list[tuple[float, str]] = []  # (projection deficit overcome, recap)
    grades: list[tuple[tuple[int, int], str, str]] = []  # (sort key, grade, label)

    for league in leagues:
        for matchup in league.matchups:
            teams = matchup.teams
            if len(teams) != 2:
                logger.warning(
                    "Skipping matchup with %s teams in league %s", len(teams), league.name
                )
                continue
            names = [display_team_name(decode_name(team.name), team_names) for team in teams]
            labels = [f"{name} ({league.name})" for name in names]
            points = [float(team.team_points.total) for team in teams]
            projections = [_projected_points(team) for team in teams]

            diff = round(abs(points[0] - points[1]), 2)
            matchup_recaps.append((diff, _recap(league.name, names, points)))

            winner = None if points[0] == points[1] else max((0, 1), key=lambda i: points[i])
            for index in (0, 1):
                result = "tie" if winner is None else ("win" if index == winner else "loss")
                games.append(
                    _TeamGame(
                        league=league.name,
                        label=labels[index],
                        points=points[index],
                        projected=projections[index],
                        result=result,
                    )
                )

            if winner is not None and None not in projections:
                loser = 1 - winner
                deficit = round(projections[loser] - projections[winner], 2)
                if deficit > 0:
                    upsets.append(
                        (
                            deficit,
                            f"In {league.name}, {names[winner]} "
                            f"(projected {projections[winner]}) upset {names[loser]} "
                            f"(projected {projections[loser]}) "
                            f"{points[winner]} - {points[loser]}",
                        )
                    )

            label_by_key = {
                getattr(team, "team_key", None): label
                for team, label in zip(teams, labels, strict=True)
            }
            for matchup_grade in getattr(matchup, "matchup_grades", None) or []:
                grade = decode_name(getattr(matchup_grade, "grade", "") or "")
                key = _grade_key(grade)
                label = label_by_key.get(getattr(matchup_grade, "team_key", None))
                if key is None or label is None:
                    continue
                grades.append((key, grade, label))

    if not games:
        return None

    closest = min(matchup_recaps, key=lambda item: item[0])
    blowout = max(matchup_recaps, key=lambda item: item[0])
    top = max(games, key=lambda game: game.points)
    low = min(games, key=lambda game: game.points)

    losers = [game for game in games if game.result == "loss"]
    winners = [game for game in games if game.result == "win"]
    unluckiest = max(losers, key=lambda game: game.points) if losers else None
    luckiest = min(winners, key=lambda game: game.points) if winners else None

    projected_games = [game for game in games if game.projected is not None]
    overachiever = underachiever = None
    if projected_games:
        over = max(projected_games, key=lambda game: game.points - game.projected)
        margin = round(over.points - over.projected, 2)
        if margin > 0:
            overachiever = Superlative(
                value=margin,
                recap=(
                    f"{over.label} beat their projection by {margin} "
                    f"({over.points} vs {over.projected})"
                ),
            )
        under = min(projected_games, key=lambda game: game.points - game.projected)
        shortfall = round(under.projected - under.points, 2)
        if shortfall > 0:
            underachiever = Superlative(
                value=shortfall,
                recap=(
                    f"{under.label} fell short of their projection by {shortfall} "
                    f"({under.points} vs {under.projected})"
                ),
            )

    upset = max(upsets, key=lambda item: item[0]) if upsets else None
    best_grade, worst_grade = _grade_awards(grades)

    median = round(statistics.median(game.points for game in games), 2)
    counts: dict[str, list[int]] = {}
    for game in games:
        entry = counts.setdefault(game.league, [0, 0])
        entry[1] += 1
        if game.points > median:
            entry[0] += 1

    return WeeklyAwards(
        closest_game=Superlative(value=closest[0], recap=closest[1]),
        biggest_blowout=Superlative(value=blowout[0], recap=blowout[1]),
        top_score=Superlative(value=top.points, recap=f"{top.label} scored {top.points}"),
        lowest_score=Superlative(value=low.points, recap=f"{low.label} scored {low.points}"),
        unluckiest_loser=Superlative(
            value=unluckiest.points,
            recap=f"{unluckiest.label} lost despite scoring {unluckiest.points}",
        )
        if unluckiest
        else None,
        luckiest_winner=Superlative(
            value=luckiest.points,
            recap=f"{luckiest.label} won with only {luckiest.points}",
        )
        if luckiest
        else None,
        overachiever=overachiever,
        underachiever=underachiever,
        upset=Superlative(value=upset[0], recap=upset[1]) if upset else None,
        best_grade=best_grade,
        worst_grade=worst_grade,
        median_score=median,
        above_median=tuple(
            LeagueMedianCount(league=league, above=above, teams=teams)
            for league, (above, teams) in counts.items()
        ),
    )
