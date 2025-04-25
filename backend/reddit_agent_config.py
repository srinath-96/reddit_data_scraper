# backend/reddit_agent_config.py

AGENT_NAME = "reddit_scraper_agent_v1"

AGENT_DESCRIPTION = "An agent that uses a tool to scrape data from a specified subreddit."

AGENT_INSTRUCTION = """Your task is to scrape data from Reddit.
You will be given the subreddit name, time filter, and limit.
Use the 'reddit_subreddit_scraper_tool' with the provided parameters to fetch the data.
Report back the result status and message from the tool. If the tool returns data, indicate how many posts were scraped.
"""

EXPECTED_TOOLS = ['reddit_subreddit_scraper_tool']