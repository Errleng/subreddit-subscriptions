import time

import imgspy
from flask import json

from globals import config, lock, reddit


def is_valid_thumbnail(thumbnail):
    return (len(thumbnail) > 0) and (thumbnail != 'default') and (thumbnail != 'nsfw')


def remove_outdated(cache):
    filtered_cache = {}
    for post_id, post in cache.items():
        if post['hours_since_creation'] <= config['display'].getfloat('outdated_threshold'):
            filtered_cache[post_id] = post
        else:
            print('removed outdated post {0} "{1}"'.format(post_id, post['title']))
    return filtered_cache


def save_cache(post_cache, subreddit_name=None):
    cache_file = config['paths']['cache_path']
    with lock:
        if subreddit_name is not None:
            print("{} acquired lock".format(subreddit_name))
        old_post_cache = None
        try:
            with open(cache_file, 'r') as f:
                old_post_cache = json.load(f)
        except FileNotFoundError:
            pass
        # merge data
        if old_post_cache is not None:
            # remove outdated
            old_post_cache = remove_outdated(old_post_cache)
            # update posts if they are newer
            for post_id, post in post_cache.items():
                if post_id in old_post_cache:
                    old_post = old_post_cache[post_id]
                    # if the post is newer, it will be older in either hours or just minutes
                    post_time = post['hours_since_creation'] * 60 + post['minutes_since_creation']
                    old_post_time = old_post['hours_since_creation'] * 60 + old_post['minutes_since_creation']
                    if post_time > old_post_time:
                        old_post_cache[post_id] = post
                        print('lock: {}, updated post: {}\n{}\n{}'.format(lock, post['title'], old_post,
                                                                          old_post_cache[old_post['id']]))
                else:
                    # the post is new
                    old_post_cache[post_id] = post
                    print('new post {}'.format(post['title']))
            post_cache = old_post_cache
        try:
            with open(cache_file, 'w') as f:
                json.dump(post_cache, f)
        except FileNotFoundError:
            pass
        try:
            with open(cache_file, 'r') as f:
                new_post_cache = json.load(f)
                print("OLD = NEW? {}".format(new_post_cache == old_post_cache))
        except FileNotFoundError:
            pass

        if subreddit_name is not None:
            print("{} released lock".format(subreddit_name))


def update_post_time_data(post, submission):
    if 'created_utc' not in post:
        post['created_utc'] = submission.created_utc
    elapsed_seconds = int(time.time() - post['created_utc'])
    elapsed_hours, elapsed_seconds = divmod(elapsed_seconds, 3600)
    elapsed_hours = int(elapsed_hours)
    post['hours_since_creation'] = elapsed_hours
    elapsed_minutes, elapsed_seconds = divmod(elapsed_seconds, 60)
    elapsed_minutes = int(elapsed_minutes)
    post['minutes_since_creation'] = elapsed_minutes
    if elapsed_hours > 0:
        post['time_since_creation'] = '{} hours ago'.format(elapsed_hours)
    elif elapsed_minutes > 0:
        post['time_since_creation'] = '{} minutes ago'.format(elapsed_minutes)
    else:
        post['time_since_creation'] = '{} seconds ago'.format(elapsed_seconds)

    return post


def update_cached_post(cached_post):
    # get submission object
    submission = reddit.submission(id=cached_post['id'])

    # update attributes
    cached_post['score'] = submission.score
    cached_post['upvote_ratio'] = int(submission.upvote_ratio * 100)
    cached_post['comment_count'] = submission.num_comments

    if 'removed_by_category' not in cached_post and hasattr(submission, 'removed_by_category'):
        cached_post['removed_by_category'] = submission.removed_by_category

    # update time data
    cached_post = update_post_time_data(cached_post, submission)

    # update time data for clicked post
    if 'visited' in cached_post:
        # post has been visited before
        elapsed_seconds = int(time.time() - cached_post['visit_time'])
        elapsed_hours, elapsed_seconds = divmod(elapsed_seconds, 3600)
        elapsed_hours = int(elapsed_hours)
        cached_post['hours_since_visit'] = elapsed_hours
        elapsed_minutes, elapsed_seconds = divmod(elapsed_seconds, 60)
        elapsed_minutes = int(elapsed_minutes)
        cached_post['minutes_since_visit'] = elapsed_minutes
        if elapsed_hours > 0:
            cached_post['time_since_visit'] = '{} hours ago'.format(elapsed_hours)
        elif elapsed_minutes > 0:
            cached_post['time_since_visit'] = '{} minutes ago'.format(elapsed_minutes)
        else:
            cached_post['time_since_visit'] = '{} seconds ago'.format(elapsed_seconds)
        cached_post['new_comment_count'] = cached_post['comment_count'] - cached_post['visit_comment_count']

    return cached_post


def get_image(submission):
    # image media
    submission_image = None
    submission_images = []

    lazy_load_start_time = time.time()

    if is_valid_thumbnail(submission.thumbnail):
        # print('{0} thumbnail "{1}"'.format(submission.title, submission.thumbnail))
        submission_image = submission.thumbnail
        # print('Using thumbnail for image preview: {0}'.format(image_preview))

    if hasattr(submission, 'preview'):
        # print('Time to lazy load: {0}'.format(time.time() - lazy_load_start_time))
        # submission has preview image
        preview_resolutions = submission.preview['images'][0]['resolutions']
        # print(len(preview_resolutions), preview_resolutions)
        if len(preview_resolutions) > 0:
            # cannot trust reddit to report accurate resolutions
            # images are often larger than reported
            # network request is the main bottleneck
            # request + PIL is slower than headers
            submission_image = preview_resolutions[0]['url']

            # go from largest to smallest because most preview images are small
            for preview_image in reversed(preview_resolutions):
                response = None
                tries = 0
                while response is None and tries < 10:
                    try:
                        response = imgspy.info(preview_image['url'])
                    except Exception as e:
                        print(
                            'Exception retrieving image information for submission {0} "{1}" with image preview {2}: {3}'.format(
                                submission.id, submission.title, preview_image, e))
                        tries += 1
                if response is not None:
                    width, height = response['width'], response['height']
                    dimensions_ratio = width / height
                    if dimensions_ratio <= config['media'].getfloat('max_width_to_height_ratio') and width <= config[
                        'media'].getfloat('max_width') and height <= config['media'].getfloat('max_height'):
                        # print('preview images stopped at ({0}, {1}) with ratio {2}'.format(width, height, dimensions_ratio))
                        submission_image = preview_image['url']
                        break
            if submission_image is None:
                submission_image = submission.preview['images'][0]['source']['url']
        else:
            submission_image = submission.preview['images'][0]['source']['url']
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

    if hasattr(submission, 'is_gallery') and submission.is_gallery:
        # Reddit now has image galleries
        if hasattr(submission, 'gallery_data') and submission.gallery_data is not None:  # check if gallery is deleted
            gallery_images = submission.gallery_data['items']
            for gallery_image in gallery_images:
                media_id = gallery_image['media_id']
                # use media_metadata attribute
                metadata = submission.media_metadata[media_id]
                # e = media type, m = extension, s = preview image, p = preview images, id = id
                # just use the first image's preview for now
                gallery_previews = metadata['p']
                # print(gallery_previews)
                preview_index = min(1, len(gallery_previews) - 1)  # sometimes the images are too small
                submission_images.append(gallery_previews[preview_index]['u'])
        else:
            print(f'Submission {submission.id} gallery is deleted')
    else:
        submission_images.append(submission_image)
    return submission_images


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
                #     print('oembed\n{0}'.format(oembed)3
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


def is_post_visible(current_post, cached_post):
    # do not displayed visited posts which have not changed
    if 'visited' in cached_post:
        # ignore post if comment count increase is less than or equal to 10%
        delta_comments = current_post.num_comments - cached_post['visit_comment_count']
        enough_new_comments = delta_comments > int(
            cached_post['visit_comment_count'] * config['display'].getfloat('comment_count_update_threshold'))

        # want to show posts that have been removed
        recently_removed = ('removed_by_category' not in cached_post or cached_post[
            'removed_by_category'] == 'null') and hasattr(current_post,
                                                          'removed_by_category') and current_post.removed_by_category is not None

        if not (enough_new_comments or recently_removed):
            return False
    elif cached_post['display_count'] >= config['display'].getint('display_count_threshold'):
        # hide posts seen too many times
        print(
            f'Post {cached_post["id"]} is over the display count threshold ({cached_post["display_count"]} vs {config["display"].getint("display_count_threshold")})')
        return False
    return True


def get_posts(submissions, score_degradation=None):
    post_cache = {}

    # session method
    # if "post_cache" not in session:
    #     session["post_cache"] = {}
    # post_cache = session["post_cache"]

    # serialization method
    try:
        with lock:
            with open(config['paths']['cache_path'], 'r') as f:
                post_cache = json.load(f)
                post_cache = remove_outdated(post_cache)
    except FileNotFoundError:
        pass

    posts = []
    top_score = None
    for submission in submissions:
        start_time = time.time()

        # get generic submission data
        post = {}

        if submission.id in post_cache:
            # handle cached post
            post = post_cache[submission.id]
            if is_post_visible(submission, post):
                post = update_cached_post(post)
                posts.append(post)
        else:
            # handle new post
            # attributes that do not need to be updated
            post['id'] = submission.id
            post['title'] = submission.title
            post['subreddit'] = submission.subreddit.display_name
            post['shortlink'] = submission.shortlink
            post['score'] = submission.score
            post['upvote_ratio'] = int(submission.upvote_ratio * 100)
            post['comment_count'] = submission.num_comments
            post['display_count'] = 1  # how many times the post was DISPLAYED
            # post['creation_time'] = submission.created_utc

            if hasattr(submission, 'removed_by_category') and submission.removed_by_category is not None:
                post['removed_by_category'] = submission.removed_by_category

            post = update_post_time_data(post, submission)

            if not submission.is_self:
                # media data
                media_preview = get_media(submission)
                if media_preview is not None:
                    post['media_preview'] = media_preview
                else:
                    image_previews = get_image(submission)
                    if image_previews and None not in image_previews:
                        print(f'{submission.id}: {image_previews}')
                        post['image_previews'] = image_previews
                # print("media", time.time() - start_time)

            print('{0} - {1}, time: {2}, visited: {3}, display_count: {4}\n'.format(post['shortlink'], post['title'],
                                                                                    round(time.time() - start_time, 4),
                                                                                    'visited' in post,
                                                                                    post['display_count']))
            posts.append(post)
        post_cache[submission.id] = post

        if score_degradation is not None:
            if top_score is None:
                top_score = int(post['score'])
            else:
                percent_change = (top_score - int(post['score'])) / top_score
                if percent_change > score_degradation:
                    print(
                        "Ending at this post because percentage change between top score ({}) and post score ({}) is {}".format(
                            top_score, int(post['score']), percent_change))
                    break

    save_cache(post_cache)

    return posts


def get_image_posts(submissions):
    image_submissions = []

    for submission in submissions:
        if len(image_submissions) >= config['display'].getint('submission_number'):
            break
        if submission.is_self:
            continue

        # Check if submission has image
        is_image_post = hasattr(submission, 'thumbnail') or hasattr(submission, 'preview')
        if is_image_post:
            image_submissions.append(submission)

    # for image_submission in image_submissions:
    #     print('{0}: {1}: {2}'.format(image_submission.shortlink, image_submission.score, image_submission.url))

    posts = []
    for image_submission in image_submissions:
        start_time = time.time()
        image_url = image_submission.url

        post = {'id': image_submission.id,
                'title': image_submission.title,
                'subreddit': image_submission.subreddit.display_name,
                'score': image_submission.score,
                'shortlink': image_submission.shortlink}

        media_preview = get_media(image_submission)
        if media_preview is not None:
            post['media_preview'] = media_preview
        else:
            post['image_url'] = image_url
            image_previews = get_image(image_submission)
            post['image_previews'] = image_previews

        posts.append(post)
        print('Done post in {0} seconds'.format(round(time.time() - start_time, 2)))

    return posts


def get_cached_posts(subreddit_name, min_hours=None, max_hours=None, score_degradation=None):
    # this uses a for loop to find posts of certain subreddits
    # however, most of the slow down is caused by updating data for posts

    try:
        with lock:
            with open(config['paths']['cache_path'], 'r') as f:
                post_cache = json.load(f)
                remove_outdated(post_cache)
    except FileNotFoundError:
        return

    posts = []

    for post_id, post in post_cache.items():
        # filter posts for subreddit
        if post['subreddit'] != subreddit_name:
            continue

        # filter posts for time range
        submission = reddit.submission(id=post['id'])
        post = update_post_time_data(post, submission)
        if min_hours is not None:
            if post['hours_since_creation'] < min_hours:
                continue
        if max_hours is not None:
            if post['hours_since_creation'] > max_hours:
                continue

        # do not displayed visited posts which have not changed
        if 'visited' in post:
            delta_comments = submission.num_comments - post['visit_comment_count']
            # ignore post if comment count increase is less than or equal to 10%
            if delta_comments > int(
                    post['visit_comment_count'] * config['display'].getfloat('comment_count_update_threshold')):
                posts.append(update_cached_post(post))
        else:
            posts.append(update_cached_post(post))

    # sort posts by score in descending order
    posts.sort(key=lambda item: item['score'], reverse=True)

    # score degradation
    if score_degradation is not None:
        top_score = None
        for i in range(len(posts)):
            post = posts[i]
            if top_score is None:
                top_score = int(post['score'])
            else:
                percent_change = (top_score - int(post['score'])) / top_score
                if percent_change > score_degradation:
                    print(
                        "Ending at this post because percentage change between top score ({}) and post score ({}) is {}".format(
                            top_score, int(post['score']), percent_change))
                    posts = posts[:-(i - 1)]
                    break

    for post in posts:
        if 'display_count' not in post:
            post['display_count'] = 1
        print(
            '{0} - {1}, visited: {2}, display_count: {3}\n'.format(post['shortlink'], post['title'], 'visited' in post,
                                                                   post['display_count']))

    save_cache(post_cache, subreddit_name=subreddit_name)

    return posts
