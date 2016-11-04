import nfldb
import csv
import os

#get current directory
cwd = os.getcwd()

#get a DB connection
db = nfldb.connect()

#get current status of the season
db_season_phase = nfldb.current(db)[0] #can be preseacon, regular, or postseason
db_season_year = nfldb.current(db)[1] #current season year
db_current_week = nfldb.current(db)[2] #current week of this season phase

#base path where we save our csvs
CSV_BASE = cwd + '\\output\\'

#config which weeks we want to look at for playoffs
MY_PLAYOFFS = range(12, 16)
ALL_REG_SEASON_LEFT = range(db_current_week+1, 18)
PLAYOFFS = MY_PLAYOFFS

#positions are the positions we're going to get rankings for
positions = ['QB', 'RB', 'WR', 'TE', 'K']

#positions_sort is used later to figure out the best position player out of a group
positions_sort = {
    'QB': 'passing_yds',
    'RB': 'rushing_yds',
    'WR': 'receiving_yds',
    'TE': 'receiving_yds',
    'K': 'kicking_fgm'
}
