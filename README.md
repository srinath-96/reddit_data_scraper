# reddit_data_scraper
Made a fun little Reddit scraper to create reddit datasets. 

## Features

* **Graphical User Interface:** Simple UI built with Flet allows users to specify the target subreddit.
* **ADK Agent:** Uses Google ADK to manage the workflow, calling a dedicated tool for scraping.
* **Reddit Scraping:** Leverages PRAW to fetch top posts and associated comments from a specified subreddit and time frame.
* **Data Output:** Saves scraped data (post details, comments, timestamps, scores, etc.) into timestamped JSON files in the `reddit_data/` directory.
* **Configuration:** Uses a `.env` file for secure handling of API keys.

## Setup and Installation

**Prerequisites:**
* Python 3.9+ (due to `asyncio.to_thread`)
* Git (for cloning)

**Steps:**

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/srinath-96/reddit_data_scrape
    cd reddit_data_scrape
    ```

2.  **Create and Activate Virtual Environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
    ```

3.  **Install Dependencies:**
    * Create a `requirements.txt` file with the following content:
        ```txt
        flet
        praw
        python-dotenv
        google-adk
        google-generativeai
        ```
    * Install the requirements:
        ```bash
        pip install -r requirements.txt
        ```
        *(Note: The exact package name for `google-adk` might vary depending on how you installed it. Adjust if necessary.)*

      ## Configuration

This application requires API keys for Google (for the ADK agent) and Reddit (for PRAW scraping).

1.  **Create `.env` File:**
    Create a file named `.env` in the root directory (`reddit_scraper_project/`).

2.  **Add API Keys:**
    Paste the following into your `.env` file and replace the placeholder values with your actual keys:

    ```dotenv
    # .env file

    # --- Google API Key (for ADK/Gemini) ---
    # Get from Google AI Studio: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
    GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY_HERE"

    # --- Reddit API Credentials ---
    # Get by creating a 'script' app at: [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
    REDDIT_CLIENT_ID="YOUR_REDDIT_CLIENT_ID_HERE"
    REDDIT_CLIENT_SECRET="YOUR_REDDIT_CLIENT_SECRET_HERE"
    # User agent format: <platform>:<app_id>:<version> by u/<your_reddit_username>
    REDDIT_USER_AGENT="Python:RedditScraperADK:v1.0 by u/your_username" # Use your actual username

    # --- Optional: ADK/App Configuration ---
    # ADK_MODEL_STRING="gemini-1.5-flash-latest"
    # APP_NAME="RedditScraperApp"
    # USER_ID="default_user"
    ```

3.  **Get Your Keys:**
    * **Google API Key:** Visit [Google AI Studio](https://aistudio.google.com/app/apikey) and create/copy your key.
    * **Reddit Credentials:**
        * Go to [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps).
        * Create a new app (select type `script`).
        * Copy the `client ID` (under the app name) and the `secret`.
        * Create a unique `user agent` string as described in the `.env` example.

## Running the Application

1.  Ensure your virtual environment is activated (`source .venv/bin/activate`).
2.  Make sure your `.env` file is created and populated with your keys.
3.  Run the Flet application:
    ```bash
    python reddit_flet_app.py
    ```
4.  The Flet window will appear. Enter the desired subreddit name and click the "Scrape Subreddit (ADK)" button.
5.  Logs will appear in the Flet app window and the terminal.
6.  Successful scrapes will save a JSON file to the `reddit_data` directory.

## How It Works

1.  The **Flet UI** (`reddit_flet_app.py`) captures the subreddit input.
2.  Clicking the button triggers the `run_reddit_scrape_with_adk` function in `backend/reddit_backend_processor.py` (running in a background thread).
3.  The backend processor initializes the **PRAW client** and the **ADK components** (`Agent`, `Runner`, `SessionService`), reading API keys via `backend/config.py`.
4.  It creates an **ADK Agent** configured with instructions and the `reddit_subreddit_scraper_tool_wrapper` tool.
5.  The processor sends a prompt to the **ADK Runner** instructing the agent to use the tool with the specified subreddit, time filter, and limit.
6.  The ADK Agent decides to use the tool, invoking the `reddit_subreddit_scraper_tool_wrapper`.
7.  The wrapper calls the `async` internal logic in `backend/reddit_adk_tool.py`.
8.  This logic uses `asyncio.to_thread` to run the synchronous **PRAW scraping** function (`scrape_subreddit` in `backend/reddit_scraper.py`) without blocking the async loop.
9.  The scraped data is returned through the wrapper to the ADK agent/runner framework.
10. The backend processor detects the **`function_response` event**, extracts the successful data, and saves it as a **JSON file** in `reddit_data/`.
11. Status updates are sent back to the Flet UI via the `log_callback`.
