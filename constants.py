# api
REDDIT_USERNAME = 'InformalTree'
REDDIT_PASSWORD = 'cFbwWxk5xKNUG2QV'
REDDIT_APP_ID = 'o9iLSYIEERtOmQ'
REDDIT_APP_SECRET = 'hPDrJLiMKzMBAFbeEBlSmNLAy7w'
REDDIT_APP_USER_AGENT = 'image-viewer by /u/InformalTree'

# image and media
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png']
MAX_WIDTH = 10000
MAX_HEIGHT = 700
MAX_WIDTH_TO_HEIGHT_RATIO = 10

# submission display
SUBMISSION_NUMBER = 10
SUBREDDIT_MAX_POSTS = 10
POST_STEP = SUBREDDIT_MAX_POSTS
SUBMISSION_SCORE_DEGRADATION = 0.8
COMMENT_COUNT_UPDATE_THRESHOLD = 0.1  # percent comment count must change by for the post to be shown again

# paths
SUBREDDIT_NAMES_RELATIVE_PATH = '../favorite-subreddits.txt'
STORAGE_DIRECTORY = 'storage'
CACHE_FILE_NAME = STORAGE_DIRECTORY + '/cache.json'

# behavior
DISPLAY_COUNT_THRESHOLD = 2
OUTDATED_THRESHOLD = 24 * 4  # in hours
SLOW_MODE = True
DEBUG_MODE = False
