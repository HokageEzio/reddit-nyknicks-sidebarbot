"""
Runs Knicks bots every minute. This is the main entry point for the heroku app.

See https://devcenter.heroku.com/articles/clock-processes-python.
See https://able.bio/rhett/how-to-set-and-get-environment-variables-in-python--274rgt5.
"""

from apscheduler.schedulers.blocking import BlockingScheduler
from constants import UTC
from datetime import datetime
from decouple import config
from game_thread_bot import GameThreadBot
from services.nba_service import NbaService
import logging.config
import os
import praw
import sidebarbot


sched = BlockingScheduler()
logging.config.fileConfig('logging_heroku.conf')
logger = logging.getLogger('main')
gdlogger = logging.getLogger('game_thread_bot')
sblogger = logging.getLogger('sidebarbot')
nba_service = NbaService(gdlogger)

class Config:
  """Container for reddit environment variables."""

  def __init__(
      self,
      client_id,
      client_secret,
      password,
      subreddit_name='knicklejerk',
      username='nyknicks-automod',
      user_agent='python-praw'):
    self.client_id = client_id
    self.client_secret = client_secret
    self.password = password
    self.subreddit_name = subreddit_name
    self.username = username
    self.user_agent = user_agent

  @staticmethod
  def from_env_vars():
    return Config(
        client_id=config('client_id'),
        client_secret=config('client_secret'),
        password=config('password'),
        subreddit_name=config('subreddit_name', 'nyknicks'),
        username=config('username', 'nyknicks-automod'),
        user_agent=config('user_agent', 'python-praw'))

  def reddit(self):
    return praw.Reddit(
        client_id=self.client_id,
        client_secret=self.client_secret,
        password=self.password,
        username=self.username,
        user_agent=self.user_agent)


@sched.scheduled_job('interval', minutes=1)
def every_minute():
  cfg = Config.from_env_vars()
  now = datetime.now(UTC)

  logger.info('Logging in to reddit.')
  logger.info(f'Using subreddit "{cfg.subreddit_name}" and user "{cfg.username}".')
  reddit = cfg.reddit()

  sidebarbot.execute(sblogger, now, reddit, cfg.subreddit_name)
  GameThreadBot(gdlogger, nba_service, now, reddit, cfg.subreddit_name, 0).run()
  logger.info('Done.')

sched.start()
