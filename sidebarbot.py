from dateutil import tz
from time import sleep

import dateutil.parser
import getpass
import json
import praw
import re
import requests

EASTERN_TIMEZONE = tz.gettz('America/New_York')
SUBREDDIT_NAME = 'knicklejerk'

def update_schedule(reddit):
  subreddit = reddit.subreddit(SUBREDDIT_NAME)

  print 'Fetching team data.'
  teams = get_teams()
  sleep(1)

  print 'Fetching schedule information.'
  schedule = get_schedule()

  print 'Building schedule text.'
  # FYI: We want to show to a show a total of 12 games: last + 4 prior + 7 next.
  # Get the array index of the last game played.
  last_played_idx = schedule['league']['lastStandardGamePlayedIndex']
  # Get the next 7 games.
  end_idx = min(last_played_idx + 7, len(schedule['league']['standard']))
  # Show the previous 4 games or more if we're at the end of the season.
  start_idx = max(0, last_played_idx - (4 + (end_idx - last_played_idx) % 7))

  rows = ['Date|Team|Loc|Time/Outcome', ':--|:--:|:--|:--']
  for i in range(start_idx, end_idx):
    game = schedule['league']['standard'][i]
    d = dateutil.parser.parse(game['startTimeUTC']).astimezone(EASTERN_TIMEZONE)
    date = d.strftime('%b %d') 
    time = d.strftime('%I:%M %p').lstrip('0')
    is_home_team = game['isHomeTeam']
    knicks_score = game['hTeam' if is_home_team else 'vTeam']
    opp_score = game['vTeam' if is_home_team else 'hTeam']
    opp_team_name = teams[opp_score['teamId']]['nickname']
    time_or_score = (time if knicks_score['score'] == '' 
        else winloss(knicks_score, opp_score))
    row = ('%s | [](/#%s) | %s | %s' % 
        (date, opp_team_name, 'Home' if is_home_team else 'Away', time_or_score))
    rows.append(row)
  result = '\n'.join(rows)

  print 'Querying settings.'
  descr = subreddit.mod.settings()['description']
  startmarker, endmarker = (descr.index("[](#StartSchedule)"),
      descr.index("[](#EndSchedule)") + len("[](#EndSchedule)"))
  updated_descr = descr.replace(descr[startmarker:endmarker], 
      "[](#StartSchedule)\n\n" + result + "\n\n[](#EndSchedule)")

  if updated_descr != descr:
    print 'Updating reddit settings.'
    subreddit.mod.update(description=updated_descr)  
  else:
    print 'No schedule changes.'

def get_teams():
  req = requests.get('http://data.nba.net/10s/prod/v1/2017/teams.json')
  if not req.status_code == 200:
    raise Exception('Teams request failed with status %s' % req.status_code)
  teams = json.loads(req.content)
  teams_map = dict()
  for team in teams['league']['standard']:
    teams_map[team['teamId']] = team
  return teams_map

def get_schedule():
  req = requests.get(
      'http://data.nba.net/data/10s/prod/v1/2017/teams/knicks/schedule.json')
  if not req.status_code == 200:
    raise Exception('Schedule request failed with status %s' % req.status_code)
  return json.loads(req.content)

def winloss(knicks_score, opp_score):
  kscore = int(knicks_score['score'])
  oscore = int(opp_score['score'])
  return 'Win' if kscore > oscore else 'Loss'

if __name__ == "__main__":
  password = getpass.getpass(prompt='Enter reddit password: ')
  client_secret = getpass.getpass(
      prompt='Enter client secret (It\'s here: https://www.reddit.com/prefs/apps/): ')

  print 'Logging in.'
  reddit = praw.Reddit(
      client_id='wJgBsaHZJ42LBg',
      client_secret=client_secret,
      password=password,
      user_agent='python-praw',
      username='macdoogles')

  update_schedule(reddit)
