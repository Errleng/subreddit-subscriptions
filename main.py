import praw
from prawcore import exceptions

from constants import REDDIT_APP_ID, REDDIT_APP_SECRET, REDDIT_APP_USER_AGENT

if __name__ == '__main__':
    # create a read-only reddit instance
    reddit = praw.Reddit(client_id=REDDIT_APP_ID, client_secret=REDDIT_APP_SECRET, user_agent=REDDIT_APP_USER_AGENT)

    print('Is Reddit instance is read only? {0}'.format(reddit.read_only))

    subreddit = reddit.subreddit('imsorryjon')

    # deal with quarantined subreddits
    try:
        subreddit.quaran.opt_in()
    except exceptions.Forbidden:
        pass

    submissions = subreddit.top('all', limit=10)
    submission_list = list(submissions)

    image_extensions = ['.jpg', '.jpeg', '.png']
    image_submissions = []

    for submission in submission_list:
        if submission.is_self:
            continue

        url = submission.url

        is_image_post = False
        for extension in image_extensions:
            if url.endswith(extension):
                is_image_post = True
                break

        if is_image_post:
            image_submissions.append(submission)

    for image_submission in image_submissions:
        print('{0}: {1}: {2}'.format(image_submission.shortlink, image_submission.score, image_submission.url))
