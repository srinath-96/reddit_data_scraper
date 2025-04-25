# backend/reddit_scraper.py
import praw
import datetime
import json
import traceback

# Import configuration variables loaded by config.py
try:
    from . import config
except ImportError:
    import config # Fallback if run directly or structure differs

def initialize_reddit():
    """Initializes and returns a PRAW Reddit instance using loaded config."""
    # Check if credentials were loaded successfully by config.py
    if not config.REDDIT_CLIENT_ID or not config.REDDIT_CLIENT_SECRET or not config.REDDIT_USER_AGENT:
        print("ERROR: Reddit API credentials not configured correctly in config/environment.")
        return None

    try:
        reddit = praw.Reddit(
            client_id=config.REDDIT_CLIENT_ID,
            client_secret=config.REDDIT_CLIENT_SECRET,
            user_agent=config.REDDIT_USER_AGENT,
            # Add username/password from config if needed
            # username=config.REDDIT_USERNAME,
            # password=config.REDDIT_PASSWORD,
            # read_only=True
        )
        print(f"PRAW Reddit instance created for user agent: {config.REDDIT_USER_AGENT}")
        # Optional: Verify connection (might require non-read-only)
        # try:
        #     print(f"Authenticated Reddit user: {reddit.user.me()}")
        # except Exception as auth_e:
        #     print(f"Could not get authenticated user (may be read-only): {auth_e}")
        return reddit
    except praw.exceptions.PRAWException as e:
        print(f"ERROR: Failed to initialize PRAW Reddit instance: {e}")
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"ERROR: An unexpected error occurred during PRAW initialization: {e}")
        traceback.print_exc()
        return None

def scrape_subreddit(reddit, subreddit_name, time_filter='week', limit=50, log_callback=print):
    """
    Scrapes posts and their top-level comments from a subreddit.
    (Code for scraping logic remains the same as previous version)
    """
    if not reddit:
        log_callback("ERROR: Invalid Reddit instance provided.")
        return None

    subreddit = reddit.subreddit(subreddit_name)
    scraped_data = []
    log_callback(f"Fetching top {limit} posts from r/{subreddit_name} for the past {time_filter}...")

    try:
        # Fetch top posts for the specified time filter
        for i, post in enumerate(subreddit.top(time_filter=time_filter, limit=limit)):
            if i % 10 == 0 and i > 0:
                 log_callback(f"  Fetched {i} posts so far...")

            post_data = {
                "id": post.id,
                "title": post.title,
                "score": post.score,
                "url": post.url,
                "num_comments": post.num_comments,
                "created_utc": datetime.datetime.fromtimestamp(post.created_utc, tz=datetime.timezone.utc).isoformat(),
                "body": post.selftext,
                "is_over18": post.over_18,
                "upvote_ratio": post.upvote_ratio,
                "comments": []
            }

            # Fetch top-level comments (limit to avoid excessive requests)
            try:
                post.comment_sort = 'top'
                post.comments.replace_more(limit=0) # Efficiently remove "load more"
                comment_limit = 20 # Configurable?
                processed_comments = 0
                for comment in post.comments.list():
                    if processed_comments >= comment_limit:
                        break
                    # Avoid deleted comments or authors
                    if comment.author and hasattr(comment, 'body') and comment.body != '[deleted]' and comment.body != '[removed]':
                         post_data["comments"].append({
                            "id": comment.id,
                            "author": comment.author.name,
                            "body": comment.body,
                            "score": comment.score,
                            "created_utc": datetime.datetime.fromtimestamp(comment.created_utc, tz=datetime.timezone.utc).isoformat(),
                        })
                         processed_comments += 1

            except praw.exceptions.PRAWException as comment_e:
                 log_callback(f"  Warning: Could not fetch comments for post {post.id}: {comment_e}")
            except Exception as comment_e:
                 log_callback(f"  Warning: Unexpected error fetching comments for post {post.id}: {comment_e}")


            scraped_data.append(post_data)

        log_callback(f"Finished scraping. Fetched data for {len(scraped_data)} posts.")
        return scraped_data

    except praw.exceptions.NotFound:
         log_callback(f"ERROR: Subreddit 'r/{subreddit_name}' not found or is private.")
         return None
    except praw.exceptions.PRAWException as e:
        log_callback(f"ERROR: An error occurred with PRAW during scraping: {e}")
        traceback.print_exc()
        return None
    except Exception as e:
        log_callback(f"ERROR: An unexpected error occurred during scraping: {e}")
        traceback.print_exc()
        return None