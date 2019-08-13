import random

import requests

from constants import REDDIT_USERNAME, REDDIT_PASSWORD, REDDIT_APP_ID, REDDIT_APP_SECRET, REDDIT_APP_USER_AGENT
from reddit_markovify import SubredditSimulatorText


def test_reddit_api():
    BASE_REDDIT_URL = 'https://www.reddit.com/'  # root url for interacting with the reddit api
    BASE_OAUTH_URL = 'https://oauth.reddit.com/'

    # getting access token
    post_data = {'grant_type': 'password', 'username': REDDIT_USERNAME, 'password': REDDIT_PASSWORD}
    client_auth = requests.auth.HTTPBasicAuth(REDDIT_APP_ID, REDDIT_APP_SECRET)
    headers = {'User-Agent': REDDIT_APP_USER_AGENT}  # should look unique to avoid 'too many requests error'
    access_token_response = requests.post(BASE_REDDIT_URL + 'api/v1/access_token', data=post_data, auth=client_auth,
                                          headers=headers)
    access_token_json = access_token_response.json()
    print(access_token_json)

    # testing access token
    headers = {'Authorization': 'bearer ' + access_token_json['access_token'], 'User-Agent': REDDIT_APP_USER_AGENT}
    account_response = requests.get(BASE_OAUTH_URL + 'api/v1/me', headers=headers)
    print(account_response.json())


def simple_markov_text_generator(texts):
    corpus = []
    markov_model = {}
    for text in texts:
        tokens = text.split()
        corpus += tokens
        for i in range(1, len(tokens)):
            preceding_token = tokens[i - 1]
            current_token = tokens[i]
            if preceding_token in markov_model.keys():
                markov_model[preceding_token].append(current_token)
            else:
                markov_model[preceding_token] = [current_token]

    for i in range(10):
        starter_word = random.choice(corpus)
        while starter_word.islower():
            starter_word = random.choice(corpus)
        chain = [starter_word]
        for j in range(30):
            chain.append(random.choice(markov_model[chain[-1]]))
        print(' '.join(chain))


def subreddit_content_generator(subreddit):
    print('\nMarkov-generated text of submissions\n')
    texts = []
    submissions = list(subreddit.top('all', limit=50))

    for submission in submissions:
        print('{0}: {1}: {2}'.format(submission.shortlink, submission.score, submission.title))
        if len(submission.selftext) > 0:
            texts.append(submission.selftext)
    print('Found {0} self posts'.format(len(texts)))

    if texts:
        corpus = '\n'.join(texts)
        text_model = SubredditSimulatorText(corpus)
        for i in range(100):
            sentence = text_model.make_sentence(tries=100, max_overlap_total=10, max_overlap_ratio=0.5)
            if sentence is not None:
                print(sentence)

    print('\nMarkov-generated text of comments\n')
    texts = []

    for submission in submissions:
        submission.comment_sort = 'top'
        submission.comments.replace_more(limit=0)
        comments = submission.comments.list()
        # texts.append('\n'.join([comment.body for comment in comments]))
        comment_bodies = []
        for i in range(int(len(comments) * 0.1) + 1):
            comment_bodies.append(comments[i].body)
        texts.append('\n'.join(comment_bodies))

    if texts:
        corpus = '\n'.join(texts)
        text_model = SubredditSimulatorText(corpus)
        for i in range(100):
            sentence = text_model.make_sentence(tries=100, max_overlap_total=10, max_overlap_ratio=0.5)
            if sentence is not None:
                print(sentence)

    print('\nMarkov-generated text of titles\n')
    texts = []

    for submission in submissions:
        texts.append(submission.title)

    if texts:
        corpus = '\n'.join(texts)
        text_model = SubredditSimulatorText(corpus)
        for i in range(100):
            sentence = text_model.make_sentence(tries=100, max_overlap_total=10, max_overlap_ratio=0.5)
            if sentence is not None:
                print(sentence)
