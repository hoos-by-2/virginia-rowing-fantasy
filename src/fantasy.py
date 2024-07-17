import os
import pandas as pd
from pathlib import Path
from yfpy.query import YahooFantasySportsQuery

from config import *

class FantasyStandings(object):
    """
    Class containing standings dataframes (one with complete data for advanced sabermetics and
    analytics, and another with basic info to be emailed out). See config.py to set default values.
    """

    def __init__(self, current_week: int, game_id="423", league_ids=league_ids, credentials_path="credentials"):
        self.current_week = current_week
        self.game_id = game_id
        self.league_ids = league_ids
        self.credentials_path = credentials_path
        self.complete_standings = pd.DataFrame(columns=complete_column_names)
        self.email_standings = None
        self.closest_game_diff = 999999999
        self.biggest_blowout_diff = 0
        self.closest_game_recap = ""
        self.biggest_blowout_recap = ""


    def get_standings(self, output_dir=output_dir):
        """
        Function to get complete and abridged (email) standings and write to output directory
        :param output_dir: Optional parameter to specify path to write output to, defaults to directory set in config
        :return: Complete and abridged overall standings dataframes
        """
        print("Getting Fantasy Standings!")
        self._create_standings_dfs()
        self.email_standings.to_csv(f"{output_dir}standings_week{self.current_week}.csv")
        print(f"Output current standings to standings_week{self.current_week}.csv")

        self.complete_standings.to_csv(f"{output_dir}complete_standings_week{self.current_week}.csv")
        print(f"Output current standings to complete_standings_week{self.current_week}.csv")

        print(f"Biggest Blowout this week ({self.biggest_blowout_diff} points): {self.biggest_blowout_recap}")
        print(f"Closest Game this week ({self.closest_game_diff} points): {self.closest_game_recap}")

        return self.complete_standings, self.email_standings

    def _create_standings_dfs(self):
        """
        Internal function to iterate over all leagues and compile dataframes for complete and abridged standings
        :return: None
        """
        for league in self.league_ids:
            self._get_complete_league_standings(league)
        self.complete_standings = self.complete_standings.sort_values(by=["Points For"], ascending=False).reset_index(drop=True)
        self.complete_standings.index += 1
        self.email_standings = self.complete_standings[email_column_names].copy()
        print("Standings DataFrames created!")

    def _get_complete_league_standings(self, league_id: str):
        """
        For the specific league passed in, get league standings and statistics
        :param league_id: League ID to get standings for
        :return: None
        """
        session = self._create_yahoo_session(league_id=league_id)
        self.get_extreme_games(session)
        #uncomment if you want to see each league's extreme games
        #self.print_extreme_games_for_league(session)

        league_name = session.get_league_metadata().name
        week = session.get_league_metadata().current_week
        if week-1 != self.current_week:
            print("Passed in week number does not match week number from data!")
        league_standings = session.get_league_standings()
        for t in (league_standings.teams):
            team = t["team"]
            team_name = team.name.decode("utf-8")
            team_name = team_name.replace("❤", "").replace("ü", "u")
            if team_name in team_names.keys():
                manager_name = team_names[team_name]
            else:
                if isinstance(team.managers, list):
                    manager_name = team.managers[0]["manager"].nickname
                else:
                    manager_name = team.managers["manager"].nickname
                print("UPDATE TEAM NAME: %s, %s" % (team_name, manager_name))

            manager_name = manager_name.replace("*", "")
            wins = team.team_standings.outcome_totals.wins
            losses = team.team_standings.outcome_totals.losses
            if team.team_standings.outcome_totals.ties != 0:
                print("TIE!!!!!!")
            points_for = team.team_standings.points_for
            points_against = team.team_standings.points_against
            point_diff = points_for - points_against
            league_rank = team.team_standings.rank
            streak = team.team_standings.streak.type[0].upper() + str(team.team_standings.streak.value)
            draft_position = team.draft_position
            draft_grade = team.draft_grade
            roster_moves = team.number_of_moves
            trades = team.number_of_trades

            row = {"Team Name": team_name, "Name": manager_name, "League": league_name, "Wins": wins,
                   "Losses": losses, "Points For": points_for, "Points Against": points_against,
                   "Point Differential": point_diff, "League Rank": league_rank, "Streak": streak,
                   "Draft Position": draft_position, "Draft Grade": draft_grade,
                   "Roster Moves": roster_moves, "Number of Trades": trades}
            self.complete_standings.loc[len(self.complete_standings.index)] = row

        print(f"Retrieved standings for {league_name}")

    def get_extreme_games(self, session):
        """
        Check's the current session's biggest blowout and closest game for the current week,
        and sets the new values if the old ones are exceeded.
        :param session: Yahoo Fantasy session
        :return: None
        """
        league_name = session.get_league_metadata().name
        scores = session.get_league_scoreboard_by_week(self.current_week)
        for matchup in scores.matchups:
            match = matchup["matchup"]
            if match.is_tied != 0:
                print("TIE!!!!!")
            recap = match.matchup_recap_title
            points = []
            names = []
            for team in match.teams:
                names.append(team["team"].name.decode())
                points.append(team["team"].team_points.total)
            diff = abs(float(points[0]) - float(points[1]))
            if diff < self.closest_game_diff:
                self.closest_game_diff = diff
                self.closest_game_recap = f"In {league_name}, {recap}"
            if diff > self.biggest_blowout_diff:
                self.biggest_blowout_diff = diff
                self.biggest_blowout_recap = f"In {league_name}, {recap}"

    def print_extreme_games_for_league(self, session):
        """
        Prints the biggest blowout and closest game for the given league and week
        :param session: Yahoo Fantasy session
        :return: None
        """
        max_diff = 0
        min_diff = 999999999
        biggest_blowout = ""
        closest_game = ""
        league_name = session.get_league_metadata().name
        scores = session.get_league_scoreboard_by_week(self.current_week)
        for matchup in scores.matchups:
            match = matchup["matchup"]
            if match.is_tied != 0:
                print("TIE!!!!!")
            recap = match.matchup_recap_title
            points = []
            names = []
            for team in match.teams:
                names.append(team["team"].name.decode())
                points.append(team["team"].team_points.total)
            diff = abs(float(points[0]) - float(points[1]))
            if diff < min_diff:
                min_diff = diff
                closest_game = recap
            if diff > max_diff:
                max_diff = diff
                biggest_blowout = recap
        print(f"Closest Game in {league_name}:")
        print(min_diff)
        print(closest_game)
        print(f"Biggest BLowout in {league_name}:")
        print(max_diff)
        print(biggest_blowout)


    def _create_yahoo_session(self, league_id: str):
        """
        Creates the Yahoo Fantasy Sports Query Session for the given league
        :param league_id: League ID
        :return: Yahoo Fantasy Sports Query Session
        """
        session = YahooFantasySportsQuery(Path(self.credentials_path), league_id=league_id, game_id=self.game_id)
        return session
