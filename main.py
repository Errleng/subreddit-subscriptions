import os
import time

import praw
from flask import Flask, render_template, request, redirect, url_for
from prawcore import exceptions

from constants import REDDIT_APP_ID, REDDIT_APP_SECRET, REDDIT_APP_USER_AGENT, SUBMISSION_NUMBER, \
    MAX_WIDTH_TO_HEIGHT_RATIO, IMAGE_EXTENSIONS, SUBREDDIT_NAMES_RELATIVE_PATH

app = Flask(__name__)
app.secret_key = b"\x9d\xbb\x95YR\n#\x1f\x91?\x8au\xfc\x8e'\xef1\xb0L\x99T^\xb76"


def get_image(submission):
    # image media
    image_preview = None

    if image_preview is None and hasattr(submission, 'preview'):
        # submission has preview image
        preview_resolutions = submission.preview['images'][0]['resolutions']
        preview = None

        # get desired preview image
        if len(preview_resolutions) >= 3:
            preview = preview_resolutions[2]
        elif len(preview_resolutions) > 0:
            preview = preview_resolutions[-1]

        if preview is not None:
            # check if preview image has acceptable width to height ratio
            image_preview_ratio = preview['width'] / preview['height']
            if image_preview_ratio <= MAX_WIDTH_TO_HEIGHT_RATIO:
                image_preview = preview['url']

    if image_preview is None and hasattr(submission, 'preview'):
        image_preview = submission.preview['images'][0]['source']['url']

    print('image_preview: {0}'.format(image_preview))

    return image_preview


def get_media(submission):
    # non-image media
    media_preview = None

    if media_preview is None and hasattr(submission, 'media_embed'):
        media_embed = submission.media_embed
        if media_embed is not None:
            if 'content' in media_embed:
                # so far known to have html for embedding the media identical to submission.media.oembed.html
                media_preview = media_embed['content']
            else:
                print('media_embed\n{0}'.format(media_embed))

    if media_preview is None and hasattr(submission, 'media'):
        media = submission.media
        if media is not None:
            if 'oembed' in media:
                # oEmbed format
                oembed = media['oembed']
                if 'html' in oembed:
                    # html for embedding the media
                    media_preview = oembed['html']
                elif 'thumbnail_url' in oembed:
                    # url to a thumbnail version of the media
                    media_preview = oembed['thumbnail_url']
                else:
                    print('oembed\n{0}'.format(oembed))
            elif 'reddit_video' in media:
                # reddit's own video player
                reddit_video = media['reddit_video']
                if 'fallback_url' in reddit_video:
                    media_preview = '<video controls><source src="{0}"></video>'.format(reddit_video['fallback_url'])
                else:
                    print('reddit_video\n{0}'.format(reddit_video))
            else:
                print('media\n{0}'.format(media))

    print('media_preview: {0}'.format(media_preview))

    return media_preview


def get_image_posts(submissions):
    image_submissions = []

    for submission in submissions:
        if len(image_submissions) >= SUBMISSION_NUMBER:
            break
        if submission.is_self:
            continue

        # Check if submission has image
        is_image_post = hasattr(submission, 'thumbnail') or hasattr(submission, 'preview')
        if is_image_post:
            image_submissions.append(submission)

    for image_submission in image_submissions:
        print('{0}: {1}: {2}'.format(image_submission.shortlink, image_submission.score, image_submission.url))

    posts = []
    for image_submission in image_submissions:
        start_time = time.time()
        image_url = image_submission.url

        post = {}
        post['title'] = image_submission.title
        post['score'] = image_submission.score
        post['shortlink'] = image_submission.shortlink

        media_preview = get_media(image_submission)
        if media_preview is not None:
            post['media_preview'] = media_preview
        else:
            post['image_url'] = image_url
            post['image_preview'] = get_image(image_submission)

        posts.append(post)
        print('Done post in {0} seconds'.format(round(time.time() - start_time, 2)))

    return posts


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        print(request.form['button'])
        if request.form['button'] == 'Subreddit search':
            subreddit_name = request.form['subreddit_search_bar']
            return redirect(url_for('view_subreddit', subreddit_name=subreddit_name, page_number=0))
        elif request.form['button'] == 'Favorite subreddits':
            return redirect(url_for('show_favorite_subreddits'))
    return render_template('index.html')


@app.route('/<subreddit_name>/<int:page_number>', methods=['GET', 'POST'])
def view_subreddit(subreddit_name, page_number):
    # create a read-only Reddit instance
    reddit = praw.Reddit(client_id=REDDIT_APP_ID, client_secret=REDDIT_APP_SECRET, user_agent=REDDIT_APP_USER_AGENT)

    print('Is Reddit instance is read only? {0}'.format(reddit.read_only))

    subreddit = reddit.subreddit(subreddit_name)

    # deal with quarantined subreddits
    try:
        subreddit.quaran.opt_in()
    except exceptions.Forbidden:
        pass

    print('Loading page {0}'.format(page_number))

    if request.method == 'POST':
        print('Next page')
        return redirect(url_for('view_subreddit', subreddit_name=subreddit_name, page_number=page_number + 1))
    else:
        submissions = subreddit.top('day')
        submissions = list(submissions)[(page_number * SUBMISSION_NUMBER):(page_number + 1) * SUBMISSION_NUMBER]
        posts = get_image_posts(submissions)
        return render_template('view_subreddit.html', subreddit_name=subreddit_name, posts=posts)


@app.route('/favorites')
def show_favorite_subreddits():
    subreddit_names = []

    # read subreddit names from a file
    script_dir = os.path.dirname(os.path.realpath(__file__))
    with open(script_dir + '/' + SUBREDDIT_NAMES_RELATIVE_PATH, 'r') as subreddit_names_file:
        for line in subreddit_names_file:
            for subreddit_name in line.split():
                subreddit_names.append(subreddit_name)

    # create a read-only Reddit instance
    reddit = praw.Reddit(client_id=REDDIT_APP_ID, client_secret=REDDIT_APP_SECRET, user_agent=REDDIT_APP_USER_AGENT)

    print('Is Reddit instance is read only? {0}'.format(reddit.read_only))

    subreddits = []

    for subreddit_name in subreddit_names:
        subreddit = reddit.subreddit(subreddit_name)

        # deal with quarantined subreddits
        try:
            subreddit.quaran.opt_in()
        except exceptions.Forbidden:
            pass

        subreddit_start_time = time.time()

        subreddit_object = {}
        subreddit_object['name'] = subreddit_name
        subreddit_object['posts'] = []

        submissions = subreddit.top('day')
        for submission in submissions:
            if len(subreddit_object['posts']) >= SUBMISSION_NUMBER:
                break

            post_start_time = time.time()

            # Get generic submission data
            post = {}
            post['title'] = submission.title
            post['score'] = submission.score
            post['shortlink'] = submission.shortlink

            media_preview = get_media(submission)
            if media_preview is not None:
                post['media_preview'] = media_preview
            elif hasattr(submission, 'thumbnail') or hasattr(submission, 'preview'):
                post['image_preview'] = get_image(submission)
                post['image_url'] = submission.url

            subreddit_object['posts'].append(post)
            print('Done post in {0} seconds'.format(round(time.time() - post_start_time, 2)))
        subreddits.append(subreddit_object)
        print('Done r/{0} in {1} seconds'.format(subreddit_name, round(time.time() - subreddit_start_time, 2)))

    return render_template('favorite_subreddits.html', subreddits=subreddits)


if __name__ == '__main__':
    app.run(debug=True)
