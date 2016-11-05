import json
import nfldb
from settings import PLAYOFFS
from settings import CSV_BASE
from settings import positions
from settings import positions_sort

#get a DB connection
db = nfldb.connect()
#get current status of the season
db_season_phase = nfldb.current(db)[0] #can be preseacon, regular, or postseason
db_season_year = nfldb.current(db)[1] #current season year
db_current_week = nfldb.current(db)[2] #current week of this season phase

player_ranks = CSV_BASE + 'player-ranks-week-' + str(db_current_week) + '.json'
fh = open(player_ranks, 'r')
player_ranks = json.load(fh)

print player_ranks['QB'][0][1]['full_name']
