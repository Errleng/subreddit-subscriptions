# Subreddit Subscriptions
Displays top posts from selected subreddits

## Notes
* Performance varies depending on the subreddit and the information requested
    * PRAW objects are lazy so some attributes may not be present until requested by use
    * For some reason, some submissions will have a 'preview' attribute while others require it to be slowly loaded
