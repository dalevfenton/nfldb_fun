import nfldb
import csv
# import os
# from pprint import pprint

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

#search the teams table and return the teams in the DB
#the DB includes an Unknown, old Jacksonville, and St Louis Rams teams we want
#to filter out since they aren't part of the current season
teams = []
with nfldb.Tx(db) as cur:
    cur.execute("SELECT * FROM team WHERE team_id NOT IN ('UNK', 'JAX', 'STL')")
    raw_teams = cur.fetchall()
    cur.close()

teams = {}


#take the RealDictRows returned from the DB query and convert them to dictionaries
#with extra attributes for each player category we can work with

for raw_team in raw_teams:
    team = dict(raw_team)
    for position in positions:
        team[position] = 0
    teams[team['team_id']] = team

#first we need to get the average score allowed by each team per position group
#so we loop through each team and we'll populate their total points given away
#per position group
for team_id, team in teams.iteritems():
    #for each team we also want to check every game they have played
    #AFAIK we can't just do as_aggregate for opposition teams for our range of weeks
    #which means we have to loop through each week of the season we have data for
    for i in range(1, db_current_week):
        #this query gets the game our team played for week i so we can find who
        #their opponent was in that week
        q = nfldb.Query(db)
        q.game( season_year=db_season_year, season_type=db_season_phase, week=i, team=team_id )
        games = q.as_games()
        #we really only have 1 game at most ( 0 on a BYE week ) but we're
        #running this as a loop anyway, could just say game = games[0]
        for game in games:
            for position in positions:
                opp = ''
                pos_score = 0.0
                #determine who the opponent was this week
                opp = game.away_team if game.home_team == team_id else game.home_team
                #get the aggregated data for the opposing players
                #for the current position we're looping through
                p = nfldb.Query(db)
                p.game( season_year=db_season_year, season_type=db_season_phase, week=i, team=team_id )
                p.player( position=position, team=opp)
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
                        # print pp.player.full_name + ' had ' + str(getattr(pp, field)) + ' ' + field + ' which counts for: ' + str(field_val) + ' each'
                        score += getattr(pp, field) * field_val
                    #set our total position score on the rating object
                    team[position] += float(format(score, '.1f'))
                    # print 'week ' + str(i) + ', ' + position + ' : ' + pp.player.full_name, str(score)
        # print team


    #WHEEEW...
    #We now have the total points scored against each team at each position based
    #on the scoring config we provided in scoring.py

    #we're still looping through each team and want to calculate the averages
    #to do that we query for the number of games our team has played so far in
    #the season, we can't just use db_current_week because of BYE weeks
    s = nfldb.Query(db)
    s.game( season_year=db_season_year, season_type=db_season_phase, week=range(1, db_current_week), team=team_id )
    games = s.as_games()
    #go ahead and do the average at each position now
    for position in positions:
        team[position] /= len(games)
    # print team


#uncomment the following lines to display a chart of the results in console
# print ' TEAM |  QB  |  RB  |  WR  |  TE  |   K  |'
# for team_id, team in teams.iteritems():
#     print ' ' + format(team_id, '4s') + ' | ' + format(team['QB'], '4.1f') + ' | ' + format(team['RB'], '4.1f') + ' | ' + format(team['WR'], '4.1f') + ' | ' + format(team['TE'], '4.1f') + ' | ' + format(team['K'], '4.1f') + ' | '

#now we don't really want a list of teams with jumbled rank values we want
#ordered rankings for each position, so we'll build out a new dictionary with
#the positions as keys and a sorted list of lists for each team and its score
ranks = {}
for position in positions:
    rank = []
    for team_id, team in teams.iteritems():
        rank.append([team_id, team[position]])
    rank.sort(key=lambda x: x[1])
    rank.reverse()
    ranks[position] = rank

ranks_output = []
count = 0
#write a row for each line of rankings
for team_id, team in teams.iteritems():
    row = []
    #each row will have its respective ranking (1, 2, 3....) for each position
    for position in positions:
        # ranks[position][count][0] is team_id, [1] is ranking value (avg pts allowed)
        row.append(ranks[position][count][0])
        row.append(ranks[position][count][1])
        # now that we know rankings let's find the teams to target for each
        # week we're interested in
        # (these are the teams from which we'd like to get players since they have good matchups)
        y = nfldb.Query(db)
        y.game( season_year=db_season_year, season_type=db_season_phase, week=PLAYOFFS, team=ranks[position][count][0] )
        y.sort([('week', 'asc')])
        # print ranks[position][count][0] + ':'
        # since there can still be BYE weeks we need to be able to see if
        # the week number has jumped since BYEs aren't returned from the query
        game_count = 0
        for game in y.as_games():
            #if the week of this game isn't the same as our start plus the number
            #of times we've looped through then we skipped a week bc of a BYE
            if( game.week != PLAYOFFS[0] + game_count):
              #append BYE to the row and throw an extra count in to pad our count
              row.append('BYE')
              game_count += 1
            #find the opposing team for this game so we can pull their players
            opp = ''
            if(game.home_team == ranks[position][count][0]):
                opp = game.away_team
            else:
                opp = game.home_team
            #query the DB to find the opposing team's players as this position
            z = nfldb.Query(db)
            z.game( season_year=db_season_year, season_type=db_season_phase, team=opp )
            z.player( position=position, team=opp)
            players = ''
            #append a cell to our row for this opponent with players sorted
            #by their likelyhood to be the guy we would want to pickup or trade for
            for pp in z.sort(positions_sort[position]).as_aggregate():
                players += ' ' + pp.player.full_name
            row.append(opp + ' - ' + players)
            game_count += 1
        row.append('  ')
    count += 1
    ranks_output.append(row)

#now that we have our rankings let's save them out to a csv so we can examine
csv_name = CSV_BASE + 'team-ranks' + str(db_current_week) + '.csv'
with open(csv_name, 'wb') as csvfile:
    csvsaver = csv.writer(csvfile, dialect=csv.excel)
    header = []

    #build the header row for our sheet
    for position in positions:
        header.append('team')
        header.append(position + ' rank')
        for week in PLAYOFFS:
            header.append('wk ' + str(week))
        header.append('  ')

    csvsaver.writerow(header)

    for row in ranks_output:
        csvsaver.writerow(row)
