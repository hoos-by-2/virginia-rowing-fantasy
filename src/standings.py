import os
import pandas as pd
from pathlib import Path

from src.logger import get_logger
from src.utils import read_yaml, post_process_standings
from src.yahoo_session import get_yahoo_session

logger = get_logger(__name__)

MAX_DIFF = float("inf")
MIN_DIFF = float("-inf")


class FantasyStandings:
    """
    Class containing standings dataframes (one with complete data for advanced sabermetics and
    analytics, and another with basic info to be emailed out). See config.yaml to set default values.
    """

    def __init__(self, config_path: str = "config.yaml", week_number: int = None):
        self.default_config = read_yaml(config_path)
        if week_number is not None:
            self.default_config['week_number'] = week_number
        self.team_names = pd.read_csv(self.default_config['team_names_path']).set_index('Team Name')['Name'].to_dict()
        #self.complete_standings = pd.DataFrame(columns=COMPLETE_COLUMN_NAMES)
        #self.email_standings = None
        self.closest_game_diff = float('inf')
        self.biggest_blowout_diff = 0
        self.closest_game_recap = ""
        self.biggest_blowout_recap = ""


    def get_standings(self, week: int = None, output_dir: str = None, get_extreme_games: bool = True):
        """
        Function to get complete and abridged (email) standings and write to output directory
        :param output_dir: Optional parameter to specify path to write output to, defaults to directory set in config
        :return: Complete and abridged overall standings dataframes
        """
        if week is None:
            week = self.default_config['week_number']
        if not isinstance(week, int) or week < 1 or week > 17:
            raise ValueError("Week must be an integer between 1 and 17")
        if output_dir is None:
            output_dir = self.default_config['output_dir']
        self.extreme_games = None
        if get_extreme_games:
            self.extreme_games = {
                "closest_game_diff": float('inf'),
                "closest_game_recap": "",
                "biggest_blowout_diff": 0,
                "biggest_blowout_recap": ""
            }
        logger.info("Getting Fantasy Standings!")
        complete_standings, email_standings = self._create_standings_dfs()

        complete_standings = post_process_standings(complete_standings)
        email_standings = post_process_standings(email_standings)

        email_standings_path = os.path.join(output_dir, f"standings_week_{week}.csv")
        complete_standings_path = os.path.join(output_dir, f"complete_standings_week_{week}.csv")

        email_standings.to_csv(email_standings_path)
        logger.info(f"Output abridged standings to {email_standings_path}")

        complete_standings.to_csv(complete_standings_path)
        logger.info(f"Output complete standings to {complete_standings_path}")

        if get_extreme_games:
            print(self.extreme_games)

        #print(f"Biggest Blowout this week ({self.biggest_blowout_diff} points): {self.biggest_blowout_recap}")
        #print(f"Closest Game this week ({self.closest_game_diff} points): {self.closest_game_recap}")

        return complete_standings, email_standings

    def _create_standings_dfs(self):
        """
        Internal function to iterate over all leagues and compile dataframes for complete and abridged standings
        :return: (complete_standings, email_standings) DataFrames
        """
        complete_standings = pd.DataFrame(columns=self.default_config['complete_column_names'])
        for league_id in self.default_config['league_ids']:
            league_standings = self.get_league_standings(league_id, self.default_config['week_number'])
            complete_standings = pd.concat([complete_standings, league_standings], ignore_index=True)
        complete_standings = complete_standings.sort_values(by=["Points For"], ascending=False).reset_index(drop=True)
        complete_standings.index += 1
        email_standings = complete_standings[self.default_config['email_column_names']].copy(deep=True)
        logger.info("Standings DataFrames created!")
        return complete_standings, email_standings

    def get_league_standings(self, league_id: str, week: int) -> pd.DataFrame:
        """
        For the specific league passed in, get league standings and statistics
        :param league_id: League ID to get standings for
        :return: None
        """
        session = get_yahoo_session(league_id=league_id, game_id=self.default_config['game_id'],
                                    credentials_path=self.default_config['credentials_path'])
        league_standings_df = pd.DataFrame(columns=self.default_config['complete_column_names'])
        if self.extreme_games is not None:
            self.get_extreme_games(session, week)
            #uncomment if you want to see each league's extreme games
            #self.print_extreme_games_for_league(session)
        league_name = session.get_league_metadata().name.decode('utf-8')
        current_week = session.get_league_metadata().current_week
        if week-1 != week:
            logger.warning(f"Passed in week number ({week}) does not match week number from data ({current_week})!")
        league_standings = session.get_league_standings()
        for team in (league_standings.teams):
            team_name = team.name.decode("utf-8")
            manager_name = ""
            if team_name in self.team_names.keys():
                manager_name = self.team_names[team_name]
            else:
                logger.warning(f"Team name not found in team names csv: {team_name}")
                if team.manager:
                    manager_name = team.manager.nickname
                elif team.managers and isinstance(team.managers, list):
                    manager_name = team.managers[0].nickname
                elif team.managers and isinstance(team.managers, dict):
                    manager_name = list(team.managers.values())[0].nickname
                else:
                    raise ValueError(f"Manager name not found for team: {team_name}")

            wins = team.team_standings.outcome_totals.wins
            losses = team.team_standings.outcome_totals.losses
            if team.team_standings.outcome_totals.ties != 0:
                logger.info(f"Tie for {team_name}")
            points_for = team.team_standings.points_for
            points_against = team.team_standings.points_against
            point_diff = round(points_for - points_against, 2)
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
            league_standings_df.loc[len(league_standings_df.index)] = row

        return league_standings_df

    def get_extreme_games(self, session, week):
        """
        Check's the current session's biggest blowout and closest game for the current week,
        and sets the new values if the old ones are exceeded.
        :param session: Yahoo Fantasy session
        :return: None
        """
        league_name = session.get_league_metadata().name.decode('utf-8')
        scores = session.get_league_scoreboard_by_week(week)
        for matchup in scores.matchups:
            if matchup.is_tied != 0:
                print("TIE!!!!!")
            recap = matchup.matchup_recap_title
            points = []
            names = []
            for team in matchup.teams:
                names.append(team.name.decode('utf-8'))
                points.append(team.team_points.total)
            diff = round(abs(float(points[0]) - float(points[1])), 2)
            if diff < self.extreme_games["closest_game_diff"]:
                self.extreme_games["closest_game_diff"] = diff
                self.extreme_games["closest_game_recap"] = f"In {league_name}, {names}"
            if diff > self.extreme_games["biggest_blowout_diff"]:
                self.extreme_games["biggest_blowout_diff"] = diff
                self.extreme_games["biggest_blowout_recap"] = f"In {league_name}, {names}"

    def print_extreme_games_for_league(self, session, week):
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
        scores = session.get_league_scoreboard_by_week(week)
        for matchup in scores.matchups:
            if matchup.is_tied != 0:
                print("TIE!!!!!")
            recap = matchup.matchup_recap_title
            points = []
            names = []
            for team in matchup.teams:
                names.append(team.name.decode('utf-8'))
                points.append(team.team_points.total)
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

