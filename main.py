import json
import time

from flask import render_template, request, redirect, url_for, jsonify, session
from prawcore import exceptions
from psaw import PushshiftAPI

from globals import config, app, reddit, lock, subreddit_names
from submissions import get_posts, remove_outdated


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

    submission_number = config['display']['submission_number']

    if request.method == 'POST':
        if 'submit_button' in request.form:
            return redirect(url_for('view_subreddit', subreddit_name=subreddit_name, page_number=page_number + 1))
        elif 'sorts' in request.form:
            if request.form['sorts'] != 'default':
                submissions = subreddit.top(request.form['sorts'])
                submissions = list(submissions)[(page_number * submission_number):(page_number + 1) * submission_number]
                posts = get_posts(submissions)
                return render_template('view_subreddit.html', subreddit_name=subreddit_name, posts=posts,
                                       sort_type=request.form['sorts'])
    else:
        submissions = subreddit.top('day')
        submissions = list(submissions)[(page_number * submission_number):(page_number + 1) * submission_number]
        posts = get_posts(submissions)
        return render_template('view_subreddit.html', subreddit_name=subreddit_name, posts=posts, sort_type='day')


@app.route('/subredditdata', methods=['POST'])
def subreddit_data_old():
    cache_file = config['paths']['cache_path']
    data = request.get_json()
    # return current subreddit name
    if len(data) == 1:
        if 'subredditIndex' in data:
            try:
                subreddit = reddit.subreddit(subreddit_names[data['subredditIndex']])
                widgets = subreddit.widgets
                # id_card is for reddit redesign, not old reddit
                id_card = widgets.id_card
                if data['subredditIndex'] < len(subreddit_names):
                    return jsonify(
                        {'subreddit_name': subreddit.display_name, 'subreddit_subscribers': subreddit.subscribers,
                         'subreddit_subscriber_text': id_card.subscribersText})
            except exceptions.Forbidden:
                # subreddit is private so skip it and return a placeholder
                return jsonify(
                    {'subreddit_name': subreddit_names[data['subredditIndex']], 'subreddit_subscribers': 0,
                     'subreddit_subscriber_text': 'subscribers'})
        elif 'clickedId' in data:
            # clicked posts are marked as such and will show changes in information
            try:
                with lock:
                    with open(cache_file, 'r') as f:
                        post_cache = json.load(f)
            except FileNotFoundError:
                return jsonify(), 404

            clicked_id = data['clickedId']
            print('Clicked {}'.format(clicked_id))
            clicked_post = post_cache[clicked_id]
            clicked_post['visited'] = True  # marks the clicked_post as clicked on
            clicked_post['visit_time'] = time.time()  # time on click
            clicked_post['visit_comment_count'] = clicked_post['comment_count']  # number of comments on click

            # save cache
            with lock:
                post_cache = None
                try:
                    with open(cache_file, 'r') as f:
                        post_cache = json.load(f)
                        post_cache = remove_outdated(post_cache)
                except FileNotFoundError:
                    pass
                if post_cache is not None:
                    post_cache[clicked_id].update(clicked_post)
                with open(cache_file, 'w') as f:
                    json.dump(post_cache, f)
            return jsonify(), 200
        elif 'viewedId' in data:
            if 'viewed_post_ids' in session:
                viewed_post_ids = session['viewed_post_ids']
            else:
                viewed_post_ids = {}

            viewed_id = data['viewedId']
            if viewed_id not in viewed_post_ids:
                viewed_post_ids[viewed_id] = None

                try:
                    with lock:
                        with open(cache_file, 'r') as f:
                            post_cache = json.load(f)
                except FileNotFoundError:
                    return jsonify(), 404

                print('Viewed {}'.format(viewed_id))
                viewed_post = post_cache[viewed_id]

                if not config['modes'].getboolean('debug_mode'):
                    viewed_post['display_count'] += 1

                # save cache
                with lock:
                    post_cache = None
                    try:
                        with open(cache_file, 'r') as f:
                            post_cache = json.load(f)
                            post_cache = remove_outdated(post_cache)
                    except FileNotFoundError:
                        pass
                    if post_cache is not None:
                        post_cache[viewed_id].update(viewed_post)
                    with open(cache_file, 'w') as f:
                        json.dump(post_cache, f)
            session['viewed_post_ids'] = viewed_post_ids
            return jsonify(), 200

        return jsonify(), 404
    # return post data
    cur_sub_num = data['subredditIndex']
    cur_post_num = data['postIndex']
    post_amount = data['postAmount']
    sort_type = data['sortType']

    if cur_sub_num >= len(subreddit_names):
        return {}

    subreddit_name = subreddit_names[cur_sub_num]
    subreddit = reddit.subreddit(subreddit_name)
    # deal with quarantined subreddits
    try:
        subreddit.quaran.opt_in()
    except exceptions.Forbidden:
        pass

    if not config['modes'].getboolean('slow_mode'):
        submissions = subreddit.top(sort_type, limit=(cur_post_num + post_amount))
        for _ in range(cur_post_num):
            try:
                next(submissions)
            except StopIteration:
                break
    else:
        # posts = get_posts(submissions, SUBMISSION_SCORE_DEGRADATION)
        # print('slow mode')
        # slow mode only shows posts older than 24 hours
        # posts which have been visited should no longer be shown because they have settled down by now
        # load cache, filter posts earlier than 24 hours
        # start_time = time.time()
        # cached_posts = get_cached_posts(subreddit.display_name, min_hours=24, max_hours=48 + 8)
        # end_time = time.time()
        # if len(cached_posts) > 0:
        #     print('using cached posts', len(cached_posts))
        #     posts = cached_posts
        # else:
        #     print('no cached posts for r/{} meet requirements'.format(subreddit.display_name))
        # print('getting cached posts took {} seconds'.format(end_time - start_time))

        # for some reason sort_type will cause duplicates to be returned
        # the submissions seemingly start duplicating / looping back
        # using a small limit such as 10 will avoid duplication
        # unknown whether using limit itself avoids duplication
        # sort_type = score is inaccurate, it is more accurate to fetch all submissions and sort them

        # PSAW API
        # this was previous initialized at the start in global scope
        # causing Pushshift API requests to get mixed up and return results from multiple API requests at once
        # initializing a new api object for each request seems to solve this problem
        api = PushshiftAPI(reddit)

        submissions = list(api.search_submissions(subreddit=subreddit_name, after='56h', before='24h'))
        id_set = set()
        for submission in submissions:
            if submission.id in id_set:
                print('{}: "{}" is duplicated'.format(submission.id, submission.title))
            else:
                id_set.add(submission.id)
            if submission.subreddit.display_name.lower() != subreddit_name.lower():
                print('submission {} of {} != subreddit {}'.format(submission.id, submission.subreddit.display_name,
                                                                   subreddit_name))
        submissions.sort(key=lambda item: item.score, reverse=True)
        submissions = submissions[:10]
        print(id_set)
        print(subreddit.display_name, submissions)
    posts = get_posts(submissions)
    print(
        f'sub #{cur_sub_num}: {subreddit.display_name}, post {cur_post_num}, {post_amount} posts, offset {cur_post_num + post_amount}, {posts}')
    return jsonify(posts)


@app.route('/subreddit/favorites')
def favorite_subreddits():
    return jsonify(subreddit_names)


@app.route('/subreddit/<subreddit_name>')
@app.route('/subreddit/<subreddit_name>/<post_amount>')
def subreddit_data(subreddit_name, post_amount=None):
    if post_amount:
        post_amount = int(post_amount)
    else:
        post_amount = config['display'].getint('subreddit_max_posts')
    subreddit = reddit.subreddit(subreddit_name)

    print(f'subreddit data, name: {subreddit_name}, amount: {post_amount}')

    if not config['modes'].getboolean('slow_mode'):
        submissions = subreddit.top('day', limit=post_amount)
    else:
        api = PushshiftAPI(reddit)
        submissions = list(api.search_submissions(subreddit=subreddit_name, after='56h', before='24h'))
        id_set = set()
        for submission in submissions:
            if submission.id in id_set:
                print('{}: "{}" is duplicated'.format(submission.id, submission.title))
            else:
                id_set.add(submission.id)
            if submission.subreddit.display_name.lower() != subreddit_name.lower():
                print('submission {} of {} != subreddit {}'.format(submission.id, submission.subreddit.display_name,
                                                                   subreddit_name))
        submissions.sort(key=lambda item: item.score, reverse=True)
        submissions = submissions[:post_amount]
        print(id_set)
        print(subreddit.display_name, submissions)
    posts = get_posts(submissions)
    return jsonify(posts)


@app.route('/favorites')
def show_favorite_subreddits():
    return render_template('favorite_subreddits.html',
                           SUBREDDIT_MAX_POSTS=config['display'].getint('subreddit_max_posts'),
                           POST_STEP=config['display'].getint('post_step'),
                           DISPLAY_COUNT_THRESHOLD=config['display'].getint('display_count_threshold'))


if __name__ == '__main__':
    app.run(debug=True, port=8080)
    # perhaps put JSON dumping here or use at exit
