import nfldb
import csv
import os
from pprint import pprint

from scoring import off_scoring_fields
from scoring import def_scoring_fields
from scoring import kicker_scoring_fields

cwd = os.getcwd()

db = nfldb.connect()
PLAYOFFS = [12, 13, 14, 15]
teams = []
with nfldb.Tx(db) as cur:
    cur.execute('SELECT * FROM team')
    raw_teams = cur.fetchall()
    cur.close()

teams = {}
teams_ignore = [{'city': 'Jacksonville', 'name': 'Jaguars', 'team_id': 'JAX'},
 {'city': 'UNK', 'name': 'UNK', 'team_id': 'UNK'},
 {'city': 'St. Louis', 'name': 'Rams', 'team_id': 'STL'}]
for ignore in teams_ignore:
    raw_teams.remove(ignore)

for raw_team in raw_teams:
    team = dict(raw_team)
    team['QB'] = 0
    team['RB'] = 0
    team['WR'] = 0
    team['TE'] = 0
    team['DST'] = 0
    team['K'] = 0
    teams[team['team_id']] = team

db_season_phase = nfldb.current(db)[0]
db_season_year = nfldb.current(db)[1]
db_current_week = nfldb.current(db)[2]

j = 0

positions = ['QB', 'RB', 'WR', 'TE', 'K']
positions_sort = { 'QB': 'passing_yds', 'RB': 'rushing_yds', 'WR': 'receiving_yds', 'TE': 'receiving_yds', 'K': 'kicking_fgm'}
for team_id, team in teams.iteritems():
    for i in range(1, db_current_week):
        q = nfldb.Query(db)
        q.game( season_year=db_season_year, season_type=db_season_phase, week=i, team=team_id )
        games = q.as_games()

        for game in games:
            ratings = {'QB': 0, 'RB': 0, 'WR': 0, 'TE':0, 'K':0 }
            for position in positions:
                opp = ''
                pos_score = 0.0
                if(game.home_team == team_id):
                    opp = game.away_team
                else:
                    opp = game.home_team
                p = nfldb.Query(db)
                p.game( season_year=db_season_year, season_type=db_season_phase, week=i, team=team_id )
                p.player( position=position, team=opp)
                for pp in p.as_aggregate():
                    score = 0.0;
                    values = {}
                    if(position == 'K'):
                        values = kicker_scoring_fields
                    else:
                        values = off_scoring_fields

                    for field, field_val in values.iteritems():
                        # print pp.player.full_name + ' had ' + str(getattr(pp, field)) + ' ' + field + ' which counts for: ' + str(field_val) + ' each'
                        score += getattr(pp, field) * field_val
                    ratings[position] += float(format(score, '.1f'))
                    # print 'week ' + str(i) + ', ' + position + ' : ' + pp.player.full_name, str(score)
            for key, value in ratings.iteritems():
                team[key] += value
        # print team
    for position in positions:
        team[position] /= db_current_week
    # print team

# print ' TEAM |  QB  |  RB  |  WR  |  TE  |   K  |'
# for team_id, team in teams.iteritems():
#     print ' ' + format(team_id, '4s') + ' | ' + format(team['QB'], '4.1f') + ' | ' + format(team['RB'], '4.1f') + ' | ' + format(team['WR'], '4.1f') + ' | ' + format(team['TE'], '4.1f') + ' | ' + format(team['K'], '4.1f') + ' | '

ranks = {}
for position in positions:
    rank = []
    for team_id, team in teams.iteritems():
        rank.append([team_id, team[position]])
    rank.sort(key=lambda x: x[1])
    rank.reverse()
    ranks[position] = rank


csv_name = cwd + '\\ranks.csv'
with open(csv_name, 'wb') as csvfile:
      csvsaver = csv.writer(csvfile, dialect=csv.excel)
      count = 0
      header = []
      for position in positions:
        header.append('team')
        header.append(position + ' rank')
        for week in PLAYOFFS:
          header.append('wk ' + str(week))
        header.append('  ')
      csvsaver.writerow(header)

      for team_id, team in teams.iteritems():
        row = []
        for position in positions:
            # print position + ':'
            row.append(ranks[position][count][0])
            row.append(ranks[position][count][1])
            y = nfldb.Query(db)
            y.game( season_year=db_season_year, season_type=db_season_phase, week=PLAYOFFS, team=ranks[position][count][0] )
            y.sort([('week', 'asc')])
            # print ranks[position][count][0] + ':'
            game_count = 0
            for game in y.as_games():
            #   print game
              if( game.week != PLAYOFFS[0] + game_count):
                row.append('BYE')
                game_count += 1
              opp = ''
              if(game.home_team == ranks[position][count][0]):
                  opp = game.away_team
              else:
                  opp = game.home_team
              z = nfldb.Query(db)
              z.game( season_year=db_season_year, season_type=db_season_phase, team=opp )
              z.player( position=position, team=opp)
              players = ''
              for pp in z.sort(positions_sort[position]).as_aggregate():
                players += ' ' + pp.player.full_name
              row.append(opp + ' - ' + players)
              game_count += 1
            row.append('  ')
        count += 1
        csvsaver.writerow(row)
