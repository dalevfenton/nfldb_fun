import nfldb
import csv
import json
# import os

from scoring import off_scoring_fields
from scoring import def_scoring_fields
from scoring import kicker_scoring_fields
from settings import PLAYOFFS
from settings import CSV_BASE
from settings import positions
from settings import positions_sort

SAVE_TO_CSV = False
SAVE_TO_JSON = True

def playerLineScore(player, player_name, pp, values, game):
    if(player.full_name == player_name):
        print 'Scoring for: ' + player_name + ' in week: ' + str(game.week)
        for field, field_val in values.iteritems():
            print format(field + ':', '8s') + '  ' + format(str(field_val), '8s') + ' * ' + format(str(getattr(pp, field)), '8s') + ' = ' + format(str(getattr(pp, field) * field_val), '8s')

def playerGames(player, game, cur_player):
    if(cur_player.full_name == player):
        print player + ' - week ' + str(game.week) + ': ' + game.home_team + ' VS ' + game.away_team

#get a DB connection
db = nfldb.connect()
#get current status of the season
db_season_phase = nfldb.current(db)[0] #can be preseacon, regular, or postseason
db_season_year = nfldb.current(db)[1] #current season year
db_current_week = nfldb.current(db)[2] #current week of this season phase

#positions_sort is used later to figure out the best position player out of a group
positions_sort = {
    'QB': 'passing_yds',
    'RB': 'rushing_yds',
    'WR': 'receiving_yds',
    'TE': 'receiving_yds',
    'K': 'kicking_fgm'
}
#take the RealDictRows returned from the DB query and convert them to dictionaries
#with extra attributes for each player category we can work with
positions = ['QB', 'RB', 'WR', 'TE', 'K']

players = {}

weeks = { 'avg': 0, 'games_played': 0 }
for i in range(1, db_current_week):
    weeks[i] = 'BYE'

for position in positions:
    position_dict = {}
    q = nfldb.Query(db)
    q.game( season_year=db_season_year, season_type=db_season_phase )
    q.player( position=position, status='Active', team__ne='UNK' )
    players_q = q.as_players()
    # print str(len(players_q)) + ' ' + position +'s found:'
    check = 0
    for player in players_q:
        s = nfldb.Query(db)
        s.game( season_year=db_season_year, season_type=db_season_phase, team=player.team, week=range(1, db_current_week))
        games = s.as_games()
        player_weeks = weeks.copy()
        player_weeks['full_name'] = player.full_name
        player_weeks['team'] = player.team
        if(len(games) > 0):
            for game in games:
                # playerGames('Jordan Payton', game, player)
                p = nfldb.Query(db)
                p.game( season_year=db_season_year, season_type=db_season_phase, week=game.week)
                p.player( position=position, full_name=player.full_name)
                pps = p.as_aggregate()
                if( len(pps) > 0 ):
                    for pp in pps:
                        score = 0.0;
                        values = {}
                        #we're just deciding which PlayPlayer fields we're going
                        #to be evaluating against here to be position appropriate
                        if(position == 'K'):
                            values = kicker_scoring_fields
                        else:
                            values = off_scoring_fields

                        #this line can be used to inspect an individual player's
                        #line item scores to make sure we're properly accounting for all scoring
                        # playerLineScore(player, 'Drew Brees', pp, values, game)

                        #loop through each field in our scoring config, add & multiply
                        #it by the value of points per (yd, td, etc)
                        for field, field_val in values.iteritems():
                            score += getattr(pp, field) * field_val

                        #set our total position score on the rating object
                        player_weeks[game.week] = score
                        player_weeks['avg'] += float(format(score, '.1f'))
                        player_weeks['games_played'] += 1
                else:
                    player_weeks[game.week] = 'OUT'
            if(player_weeks['games_played'] > 0 and player_weeks['avg'] != 0):
                player_weeks['avg'] /= player_weeks['games_played']
                position_dict[player.player_id] = player_weeks

    players[position] = position_dict

ranks = {}
for position, position_data in players.iteritems():
    rank = []
    for player_id, player_data in position_data.iteritems():
        rank.append([player_id, player_data])
        # print player_data['full_name'] + ": " + str(player_data['avg']) + "pts / wk"
    rank.sort(key=lambda x: x[1]['avg'])
    rank.reverse()
    ranks[position] = rank

# for position, position_data in ranks.iteritems():
#     print '!'*80
#     print ' '*40 + position
#     print '!'*80
#     for player in position_data:
#         print player[1]['full_name'] + ': ' + str(player[1]['avg'])

FILE_BASE = 'player-ranks-week-' + str(db_current_week)

if(SAVE_TO_JSON):
    json_file = CSV_BASE + FILE_BASE + '.json'
    fh = open(json_file, 'w')
    json.dump( ranks, fh )

if(SAVE_TO_CSV):
    #now that we have our rankings let's save them out to a csv so we can examine
    csv_name = CSV_BASE + FILE_BASE + '.csv'
    with open(csv_name, 'wb') as csvfile:
        csvsaver = csv.writer(csvfile, dialect=csv.excel)

        #build the header row for our sheet
        for position, position_data in ranks.iteritems():
            header = []
            header.append('Player')
            header.append('Team')
            header.append(position + ' Rank')
            for i in range(1, db_current_week):
                header.append('wk ' + str(i))

            csvsaver.writerow(header)
            for player in position_data:
                row = []
                data = player[1]
                row = [data['full_name'], data['team'], data['avg']]
                for i in range(1, db_current_week):
                    if(isinstance(data[i], int) or isinstance(data[i], float)):
                        row.append(data[i])
                    else:
                        t = nfldb.Query(db)
                        t.game( season_year=db_season_year, season_type=db_season_phase, week=i, team=data['team'])
                        game = t.as_games()
                        if(len(game) > 0):
                            row.append('OUT')
                        else:
                            row.append('BYE')
                csvsaver.writerow(row)
            csvsaver.writerow([' ', ' '])
