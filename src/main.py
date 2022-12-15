from fantasy import *
import logging
logging.getLogger("yfpy.query").setLevel(logging.WARNING)

if __name__ == "__main__":
    fantasy = FantasyStandings(current_week=14)
    fantasy.get_standings()
    #print(fantasy.complete_standings)



