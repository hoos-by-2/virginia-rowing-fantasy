import pandas as pd

complete_column_names = ["Team Name", "Name", "League", "Wins", "Losses", "Points For", "Points Against",
                         "Point Differential", "League Rank", "Streak", "Draft Position", "Draft Grade",
                         "Roster Moves", "Number of Trades"]

email_column_names = ["Team Name", "Name", "League", "Wins", "Losses", "Points For", "Points Against"]

league_ids = ["435399", "687576", "436480", "717708", "441275", "327657", "296941", "587757", "594694"]

output_dir = "C:/Users/student/Desktop/fantasy/2023/output/"

team_names_df = pd.read_csv('team_names.csv')
team_names = team_names_df.set_index('Team Name')['Name'].to_dict()