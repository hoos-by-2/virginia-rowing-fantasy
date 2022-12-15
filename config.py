import pandas as pd

complete_column_names = ["Team Name", "Name", "League", "Wins", "Losses", "Points For", "Points Against",
                         "Point Differential", "League Rank", "Streak", "Draft Position", "Draft Grade",
                         "Roster Moves", "Number of Trades"]

email_column_names = ["Team Name", "Name", "League", "Wins", "Losses", "Points For", "Points Against"]

league_ids = ["1131625", "190564", "340459", "564177", "829152", "733842", "703552", "230133", "1342211"]

output_dir = "C:/Users/student/Desktop/fantasy/2022/output/"

team_names_df = pd.read_csv('team_names.csv')
team_names = team_names_df.set_index('Team Name')['Name'].to_dict()