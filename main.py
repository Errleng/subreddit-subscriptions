import os
import time

import imgspy
import praw
from flask import Flask, render_template, request, redirect, url_for, jsonify
from prawcore import exceptions

from constants import REDDIT_APP_ID, REDDIT_APP_SECRET, REDDIT_APP_USER_AGENT, SUBMISSION_NUMBER, \
    MAX_WIDTH, MAX_HEIGHT, MAX_WIDTH_TO_HEIGHT_RATIO, SUBREDDIT_NAMES_RELATIVE_PATH, SUBMISSION_SCORE_DEGRADATION

app = Flask(__name__)
app.secret_key = b"\x9d\xbb\x95YR\n#\x1f\x91?\x8au\xfc\x8e'\xef1\xb0L\x99T^\xb76"

subreddit_names = []
# read subreddit names from a file
script_dir = os.path.dirname(os.path.realpath(__file__))
with open(script_dir + '/' + SUBREDDIT_NAMES_RELATIVE_PATH, 'r') as subreddit_names_file:
    for line in subreddit_names_file:
        for name in line.split():
            subreddit_names.append(name)

# create a read-only Reddit instance
reddit = praw.Reddit(client_id=REDDIT_APP_ID, client_secret=REDDIT_APP_SECRET, user_agent=REDDIT_APP_USER_AGENT)


def is_valid_thumbnail(thumbnail):
    return thumbnail != 'nsfw'


def get_image(submission):
    # image media
    submission_image = None

    lazy_load_start_time = time.time()

    if is_valid_thumbnail(submission.thumbnail):
        submission_image = submission.thumbnail
        # print('Using thumbnail for image preview: {0}'.format(image_preview))

    if hasattr(submission, 'preview'):
        print('Time to lazy load: {0}'.format(time.time() - lazy_load_start_time))
        # submission has preview image
        preview_resolutions = submission.preview['images'][0]['resolutions']
        print(len(preview_resolutions), preview_resolutions)
        # cannot trust reddit to report accurate resolutions
        # images are often larger than reported
        # network request is the main bottleneck
        # request + PIL is slower than headers
        for preview_image in reversed(preview_resolutions):
            # go from largest to smallest because most preview images are small
            response = imgspy.info(preview_image['url'])
            width, height = response['width'], response['height']
            dimensions_ratio = width / height
            if dimensions_ratio <= MAX_WIDTH_TO_HEIGHT_RATIO and width <= MAX_WIDTH and height <= MAX_HEIGHT:
                print('preview images stopped at ({0}, {1}) with ratio {2}'.format(width, height, dimensions_ratio))
                submission_image = preview_image['url']
                break
        # dimensions_ratio = image['width'] / image['height']
        # if dimensions_ratio > MAX_WIDTH_TO_HEIGHT_RATIO or image['width'] > MAX_WIDTH or image[
        #     'height'] > MAX_HEIGHT:
        #     print('preview images stopped at ({0}, {1}) with ratio {2}'.format(image['width'], image['height'],
        #                                                                       dimensions_ratio))
        #     break
        # else:
        #     print(image)
        #     image_preview = image['url']
        # else:
        #     source_image = submission.preview['images'][0]['source']
        #     if (source_image['width'] > MAX_WIDTH or source_image['height'] > MAX_HEIGHT) and is_valid_thumbnail(submission.thumbnail):
        #         image_preview = submission.thumbnail
        #         print('Using thumbnail for image preview: {0}'.format(image_preview))
        #     else:
        #         print('preview image (width, height): ({0}, {1}), url: {2}'.format(source_image['width'], source_image['height'], source_image['url']))
        #         image_preview = source_image['url']
    print(submission_image)
    return submission_image


def get_media(submission):
    # non-image media
    media_preview = None

    if media_preview is None and hasattr(submission, 'media_embed'):
        media_embed = submission.media_embed
        if media_embed is not None:
            if 'content' in media_embed:
                # so far known to have html for embedding the media identical to submission.media.oembed.html
                media_preview = media_embed['content']
            # else:
            #     print('media_embed\n{0}'.format(media_embed))

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
                # else:
                #     print('oembed\n{0}'.format(oembed))
            elif 'reddit_video' in media:
                # reddit's own video player
                reddit_video = media['reddit_video']
                if 'fallback_url' in reddit_video:
                    media_preview = '<video controls><source src="{0}"></video>'.format(reddit_video['fallback_url'])
                # else:
                #     print('reddit_video\n{0}'.format(reddit_video))
            # else:
            #     print('media\n{0}'.format(media))

    # print('media_preview: {0}'.format(media_preview))

    return media_preview


def get_posts(submissions, score_degredation=None):
    posts = []
    top_score = None
    for submission in submissions:
        start_time = time.time()

        # get generic submission data
        post = {}
        post['title'] = submission.title
        post['score'] = submission.score
        post['shortlink'] = submission.shortlink
        # upvote ratio takes a lot of time to retrieve, likely uses up another API request
        post['upvote_ratio'] = int(submission.upvote_ratio * 100)
        post['creation_time'] = submission.created_utc
        elapsed_seconds = time.time() - post['creation_time']
        elapsed_hours, elapsed_seconds = divmod(elapsed_seconds, 3600)
        if elapsed_hours > 0:
            post['elapsed_time'] = "{0} hours ago".format(int(elapsed_hours))
        else:
            elapsed_minutes, elapsed_seconds = divmod(elapsed_seconds, 60)
            post['elapsed_time'] = "{0} minutes ago".format(int(elapsed_minutes))

        if not submission.is_self:
            # media data
            media_preview = get_media(submission)
            if media_preview is not None:
                post['media_preview'] = media_preview
            elif hasattr(submission, 'thumbnail') or hasattr(submission, 'preview'):
                image_preview = get_image(submission)
                if image_preview is not None:
                    post['image_preview'] = image_preview
                post['image_url'] = submission.url
            # print("media", time.time() - start_time)

        print('{0} - {1}, time: {2}\n'.format(post['shortlink'], post['title'], round(time.time() - start_time, 4)))
        posts.append(post)

        if score_degredation is not None:
            if top_score is None:
                top_score = int(post['score'])
            else:
                percent_change = (top_score - int(post['score'])) / top_score
                if percent_change > score_degredation:
                    print(
                        "Ending at this post because percentage change between top score ({}) and post score ({}) is {}".format(
                            top_score, int(post['score']), percent_change))
                    break
    return posts


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
    subreddit = reddit.subreddit(subreddit_name)

    # deal with quarantined subreddits
    try:
        subreddit.quaran.opt_in()
    except exceptions.Forbidden:
        pass

    print('Loading page {0}'.format(page_number))

    if request.method == 'POST':
        if 'submit_button' in request.form:
            return redirect(url_for('view_subreddit', subreddit_name=subreddit_name, page_number=page_number + 1))
        elif 'sorts' in request.form:
            if request.form['sorts'] != 'default':
                submissions = subreddit.top(request.form['sorts'])
                submissions = list(submissions)[(page_number * SUBMISSION_NUMBER):(page_number + 1) * SUBMISSION_NUMBER]
                posts = get_posts(submissions)
                return render_template('view_subreddit.html', subreddit_name=subreddit_name, posts=posts,
                                       sort_type=request.form['sorts'])
    else:
        submissions = subreddit.top('day')
        submissions = list(submissions)[(page_number * SUBMISSION_NUMBER):(page_number + 1) * SUBMISSION_NUMBER]
        posts = get_posts(submissions)
        return render_template('view_subreddit.html', subreddit_name=subreddit_name, posts=posts, sort_type='day')


@app.route('/favorites', methods=['GET', 'POST'])
def show_favorite_subreddits():
    if request.method == 'POST':
        data = request.get_json()
        # return current subreddit name
        if len(data) == 1 and 'subredditIndex' in data:
            if data['subredditIndex'] < len(subreddit_names):
                return jsonify({'subreddit_name': subreddit_names[data['subredditIndex']]})
            else:
                return jsonify(), 404

        # return post data
        cur_sub_num = data['subredditIndex']
        cur_post_num = data['postIndex']
        post_amount = data['postAmount']
        sort_type = data['sortType']

        if cur_sub_num >= len(subreddit_names):
            return {}

        subreddit = reddit.subreddit(subreddit_names[cur_sub_num])
        # deal with quarantined subreddits
        try:
            subreddit.quaran.opt_in()
        except exceptions.Forbidden:
            pass

        submissions = subreddit.top(sort_type, limit=(cur_post_num + post_amount))

        print(cur_post_num, post_amount, cur_post_num + post_amount)

        for _ in range(cur_post_num):
            try:
                next(submissions)
            except StopIteration:
                break

        return jsonify(get_posts(submissions, SUBMISSION_SCORE_DEGRADATION))
    return render_template('favorite_subreddits.html')


if __name__ == '__main__':
    app.run(debug=True)
