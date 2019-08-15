import os
import time
import urllib.request
import praw
from flask import Flask, render_template, request
from prawcore import exceptions
from PIL import Image

from constants import REDDIT_APP_ID, REDDIT_APP_SECRET, REDDIT_APP_USER_AGENT

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        subreddit_name = request.form['subreddit']
        return view_subreddit(subreddit_name)
    return render_template('index.html')


@app.route('/<subreddit_name>')
def view_subreddit(subreddit_name):
    # create a read-only Reddit instance
    reddit = praw.Reddit(client_id=REDDIT_APP_ID, client_secret=REDDIT_APP_SECRET, user_agent=REDDIT_APP_USER_AGENT)

    print('Is Reddit instance is read only? {0}'.format(reddit.read_only))

    subreddit = reddit.subreddit(subreddit_name)

    # deal with quarantined subreddits
    try:
        subreddit.quaran.opt_in()
    except exceptions.Forbidden:
        pass

    submissions = subreddit.top('all')

    image_extensions = ['.jpg', '.jpeg', '.png']
    image_submissions = []

    SUBMISSION_NUMBER = 10
    for submission in submissions:
        if len(image_submissions) >= SUBMISSION_NUMBER:
            break
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

    posts = []
    dimensions = (500, 500)
    for image_submission in image_submissions:
        start_time = time.time()
        image_url = image_submission.url
        image_name = os.path.basename(image_url)
        response = urllib.request.urlopen(image_url)
        print('Done request at {0} seconds'.format(time.time() - start_time))
        image = Image.open(response)
        print('Done downloading at {0} seconds'.format(time.time() - start_time))
        image.thumbnail(dimensions)
        # image = image.resize((500, 500))
        print('Done resizing at {0} seconds'.format(time.time() - start_time))
        image.save('static/' + image_name)
        print('Done saving at {0} seconds'.format(time.time() - start_time))

        post = {}
        post['title'] = image_submission.title
        post['score'] = image_submission.score
        post['shortlink'] = image_submission.shortlink
        post['image_name'] = image_name
        post['image_url'] = image_url
        posts.append(post)
        print('Done in {0} seconds'.format(time.time() - start_time))

    print('Done processing all images')

    return render_template('view_subreddit.html', subreddit_name=subreddit_name, posts=posts)


if __name__ == '__main__':
    app.run(debug=True)

