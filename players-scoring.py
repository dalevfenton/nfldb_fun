import nfldb
import csv
# import os

from scoring import off_scoring_fields
from scoring import def_scoring_fields
from scoring import kicker_scoring_fields
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


# q = nfldb.Query(db)
# q.game( season_year=db_season_year, season_type=db_season_phase )
# q.player( position='QB' )
# players = q.as_aggregate()
# player = players[0]
# print player.player.full_name + ' : '
# print player.player

players = {}

weeks = { 'avg': 0 }
for i in range(1, db_current_week):
    weeks[i] = 'OUT'

for position in positions:
    position_dict = {}
    q = nfldb.Query(db)
    q.game( season_year=db_season_year, season_type=db_season_phase )
    q.player( position=position, status='Active', team__ne='UNK' )
    players_q = q.as_players()
    # print str(len(players_q)) + ' ' + position +'s found:'
    check = 0
    for player in players_q:
        # if check < 10:
            # print player.player_id + ' : ' + player.full_name

            player_weeks = weeks.copy()
            player_weeks['full_name'] = player.full_name
            player_weeks['team'] = player.team
            s = nfldb.Query(db)
            s.game( season_year=db_season_year, season_type=db_season_phase, week=range(1, db_current_week))
            s.player( full_name=player.full_name, status='Active')
            games = s.as_games()

            for game in games:
                p = nfldb.Query(db)
                p.game( season_year=db_season_year, season_type=db_season_phase, week=game.week)
                p.player( position=position, full_name=player.full_name)
                for pp in p.as_aggregate():
                    score = 0.0;
                    values = {}
                    #we're just deciding which PlayPlayer fields we're going
                    #to be evaluating against here to be position appropriate
                    if(position == 'K'):
                        values = kicker_scoring_fields
                    else:
                        values = off_scoring_fields
                    #loop through each field in our scoring config, add & multiply
                    #it by the value of points per (yd, td, etc)
                    for field, field_val in values.iteritems():
                        score += getattr(pp, field) * field_val
                        # if(player.full_name == 'Matt Bryant'):
                            # print format(field + ':', '8s') + '  ' + format(str(field_val), '8s') + ' * ' + format(str(getattr(pp, field)), '8s') + ' = ' + format(str(getattr(pp, field) * field_val), '8s')
                        # print pp.player.full_name + ' had ' + str(getattr(pp, field)) + ' ' + field + ' which counts for: ' + str(field_val) + ' each'

                    #set our total position score on the rating object
                    player_weeks[game.week] = score
                    player_weeks['avg'] += float(format(score, '.1f'))

                    # print 'week ' + str(game.week)
                    # print pp
                    # print score
        # check += 1
            player_weeks['avg'] /= len(games)
            # print player_weeks
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


#now that we have our rankings let's save them out to a csv so we can examine
csv_name = CSV_BASE + 'player-ranks' + str(db_current_week) + '.csv'
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
