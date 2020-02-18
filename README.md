# reddit-image-viewer
Displays media posts from subreddits

## Notes
* Performance is worse on some subreddits
    * PRAW objects are lazy so attributes may not be present until requested by use
    * For some reason, some submissions will have a 'preview' attribute while others require it to be loaded, making them slower

## Plan
* Implement option to select time period of top posts