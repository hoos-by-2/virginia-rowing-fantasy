from src.standings import FantasyStandings

import logging
logging.getLogger("yfpy.query").setLevel(logging.WARNING)

if __name__ == "__main__":
    fantasy = FantasyStandings(week_number=1)
    complete_standings, email_standings = fantasy.get_standings()
    #print(complete_standings.head(10))
