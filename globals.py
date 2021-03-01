import threading
from configparser import ConfigParser

import praw
from flask import Flask

# set up config
secret_config = ConfigParser()
secret_config.read('secrets.ini')
secrets = secret_config['secrets']
config = ConfigParser()
config.read('config.ini')

# set up globals
subreddit_names = list(filter(None, [x.strip() for x in config['user']['subreddits'].splitlines()]))

# cache read and write lock
lock = threading.Lock()

# set up Flask app
app = Flask(__name__)
app.secret_key = secrets['flask_secret_key']

# create a read-only Reddit instance
reddit = praw.Reddit(client_id=secrets['reddit_app_id'], client_secret=secrets['reddit_app_secret'],
                     user_agent=secrets['reddit_app_user_agent'])
