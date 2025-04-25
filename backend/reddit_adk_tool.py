# backend/reddit_adk_tool.py
import traceback
import praw
import asyncio # Import asyncio

# Import the scraper utility
try:
    from . import reddit_scraper
except ImportError:
    import reddit_scraper

# NOTE: reddit_instance parameter is REMOVED from the signature
async def reddit_subreddit_scraper_logic( # Make this async
    subreddit_name: str,
    time_filter: str = 'week',
    limit: int = 50,
    log_callback=print,
    reddit_instance_internal: praw.Reddit = None
) -> dict:
    """
    Internal logic to scrape subreddit. Requires reddit_instance_internal.
    Uses asyncio.to_thread to run synchronous PRAW calls.
    """
    tool_name = "reddit_subreddit_scraper_logic"
    log_callback(f"--- Internal Logic: {tool_name} executing for r/{subreddit_name} ---")

    if not reddit_instance_internal:
        msg = "Internal error: PRAW Reddit instance was not provided internally."
        log_callback(f"  [Logic Error] {msg}")
        return {"status": "error", "message": msg}
    if not subreddit_name:
        msg = "Missing required argument: subreddit_name."
        log_callback(f"  [Logic Error] {msg}")
        return {"status": "error", "message": msg}

    try:
        # --- Run synchronous PRAW code in a separate thread ---
        scraped_data = await asyncio.to_thread(
            reddit_scraper.scrape_subreddit, # Function to run
            reddit_instance_internal,        # Args for the function
            subreddit_name,
            time_filter,
            limit,
            log_callback
        )
        # --- End of threaded execution ---

        if scraped_data is None:
            return {"status": "error", "message": f"Scraping r/{subreddit_name} failed. See logs."}
        elif not scraped_data:
            msg = f"No posts found or scraped from r/{subreddit_name}."
            log_callback(f"  [Logic Info] {msg}")
            return {"status": "success", "message": msg, "data": []}
        else:
            msg = f"Successfully scraped {len(scraped_data)} posts from r/{subreddit_name} (async wrapper)."
            log_callback(f"  [Logic Success] {msg}")
            return {"status": "success", "message": msg, "data": scraped_data}

    except Exception as e:
        error_msg = f"Unexpected error in {tool_name} for r/{subreddit_name}: {e}"
        log_callback(f"  [Logic Error] {error_msg}")
        traceback.print_exc()
        return {"status": "error", "message": error_msg}