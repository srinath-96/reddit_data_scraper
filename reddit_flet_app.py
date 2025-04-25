# reddit_flet_app.py
import flet as ft
import asyncio
import threading
import traceback
import sys
import os

# --- Load .env file early ---
try:
    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    print(f"[Flet App] Attempting to load .env file from: {dotenv_path}")
    if os.path.exists(dotenv_path):
        if load_dotenv(dotenv_path=dotenv_path):
            print("[Flet App] .env file loaded successfully by Flet app.")
        else:
            print("[Flet App] Warning: .env file found but may be empty or failed to load.")
    else:
        print("[Flet App] Info: .env file not found at script location. Relying on system env vars or backend loading.")
except ImportError:
    print("[Flet App] ERROR: python-dotenv not found. Cannot load .env file.")
    print("[Flet App] Please install it: pip install python-dotenv")

# --- Add backend directory to Python path ---
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
if backend_path not in sys.path:
    print(f"[Flet App] Adding to sys.path: {backend_path}")
    sys.path.insert(0, backend_path)

# Now import the ADK-based backend processing function
try:
    from reddit_backend_processor import run_reddit_scrape_with_adk
except ImportError as e:
    print(f"[Flet App] ERROR: Could not import run_reddit_scrape_with_adk from backend.")
    print(f"ImportError: {e}")
    async def run_reddit_scrape_with_adk(*args, **kwargs):
        log_callback = kwargs.get('log_callback', print)
        log_callback("FATAL ERROR: Backend processor (ADK version) could not be loaded.")
        await asyncio.sleep(0)
        return None
except ModuleNotFoundError as e:
    print(f"[Flet App] ERROR: A required module was not found during backend import.")
    print(f"ModuleNotFoundError: {e}")
    async def run_reddit_scrape_with_adk(*args, **kwargs):
        log_callback = kwargs.get('log_callback', print)
        log_callback("FATAL ERROR: Missing dependency for backend processor.")
        await asyncio.sleep(0)
        return None

# --- Configuration ---
DEFAULT_SUBREDDIT = "wallstreetbets"
DEFAULT_TIME_FILTER = "week"
DEFAULT_LIMIT = 50
OUTPUT_DIRECTORY = "reddit_data"

# --- Flet UI Main Function ---
def main(page: ft.Page):
    page.title = "Reddit Scraper (ADK)"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.window_width = 750
    page.window_height = 700
    page.padding = 20
    page.theme_mode = ft.ThemeMode.SYSTEM

    # --- UI Controls (Using updated Icons and Colors enums) ---
    subreddit_input = ft.TextField(
        label="Subreddit Name (e.g., wallstreetbets)",
        value=DEFAULT_SUBREDDIT,
        width=300
    )
    scrape_button = ft.ElevatedButton(
        "Scrape Subreddit (ADK)",
        icon=ft.icons.DOWNLOAD_FOR_OFFLINE_OUTLINED, # Corrected: Use ft.Icons
        bgcolor=ft.colors.ORANGE_ACCENT_700,         # Corrected: Use ft.Colors
        color=ft.colors.WHITE,                   # Corrected: Use ft.Colors
        height=50,
        tooltip="Starts scraping the specified subreddit using the ADK agent"
    )
    log_output = ft.TextField(
        label="Log Output",
        value="Enter subreddit name and click scrape.\nRequires .env file with API keys (GOOGLE_API_KEY, REDDIT_CLIENT_ID, etc.).",
        read_only=True,
        multiline=True,
        expand=True,
        border_color=ft.colors.OUTLINE,          # Corrected: Use ft.Colors
        border_radius=ft.border_radius.all(5),
        min_lines=15,
        text_size=12,
    )
    progress_ring = ft.ProgressRing(visible=False, width=24, height=24, stroke_width=3)
    status_text = ft.Text("Ready", italic=True, size=11, color=ft.colors.SECONDARY) # Corrected: Use ft.Colors

    # --- State ---
    is_running = False

    # --- Functions ---
    def update_log(message: str):
        """Appends a message to the log view safely from any thread."""
        msg_str = str(message).strip()
        if not msg_str: return

        # This function runs the actual UI update.
        def update_ui_sync():
            current_value = log_output.value if log_output.value else ""
            max_log_lines = 150
            lines = current_value.split('\n')
            if len(lines) > max_log_lines: lines = lines[-max_log_lines:]
            log_output.value = "\n".join(lines) + "\n" + msg_str
            # Check if page update is needed/possible
            if page.client_storage: # A simple check if page seems alive
                 try:
                     page.update()
                 except Exception as update_e:
                     print(f"Error updating page (maybe closing?): {update_e}")
            else:
                 print(f"LOG (page seems closed): {msg_str}")


        # If page.loop exists, schedule the UI update on it.
        # This is the safe way to update Flet UI from a background thread.
        # No need to check asyncio.get_running_loop() here.
        if page.loop is not None:
            page.loop.call_soon_threadsafe(update_ui_sync)
        else:
            # Fallback if the page loop isn't running (e.g., during shutdown)
            print(f"LOG (no UI loop): {msg_str}")


    async def run_backend_task_async():
        """The async task that calls the ADK backend scraper."""
        # (This function's logic remains the same as before)
        nonlocal is_running
        subreddit = subreddit_input.value.strip()
        if not subreddit:
            update_log("ERROR: Subreddit name cannot be empty.")
            # Safely update UI state from async function using lambda with call_soon_threadsafe
            def reset_ui():
                nonlocal is_running
                is_running = False
                scrape_button.disabled = False
                progress_ring.visible = False
                status_text.value = "Error: Enter Subreddit."
                page.update()
            if page.loop: page.loop.call_soon_threadsafe(reset_ui)
            return

        update_log(f"Backend task started for r/{subreddit} (Using ADK)...")
        output_file = None
        try:
            output_file = await run_reddit_scrape_with_adk(
                subreddit_name=subreddit, time_filter=DEFAULT_TIME_FILTER,
                limit=DEFAULT_LIMIT, output_dir=OUTPUT_DIRECTORY, log_callback=update_log
            )
            if output_file:
                update_log(f"Backend task finished successfully.")
                # Update status via call_soon_threadsafe for safety from async func
                if page.loop: page.loop.call_soon_threadsafe(lambda: setattr(status_text, 'value', "Finished. Saved."))
            else:
                 update_log(f"Backend task finished with errors or no data.")
                 if page.loop: page.loop.call_soon_threadsafe(lambda: setattr(status_text, 'value', "Finished with errors/no data."))

        except Exception as e:
            update_log(f"--- FATAL ERROR in backend task ---"); update_log(traceback.format_exc())
            if page.loop: page.loop.call_soon_threadsafe(lambda: setattr(status_text, 'value', "Fatal Error."))
        finally:
            # Safely update final UI state from async function
            def final_ui_update():
                nonlocal is_running
                is_running = False
                scrape_button.disabled = False; progress_ring.visible = False
                # Check current status before potentially overwriting success/error message
                if status_text.value.startswith("Running"):
                    status_text.value = "Finished."
                elif output_file is None and status_text.value == "Ready":
                    status_text.value = "Finished with errors."
                page.update()
            if page.loop: page.loop.call_soon_threadsafe(final_ui_update)


    def run_backend_in_thread():
        """Runs the async backend task in a separate thread."""
        # Call update_log *before* starting the thread to avoid the race condition
        update_log("Starting backend thread...")

        # Define the target function for the thread
        def run_async_in_new_loop():
            # Set up a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                 # Run the main async task until it completes
                 loop.run_until_complete(run_backend_task_async())
            finally:
                 # Cleanly close the loop
                 loop.close()
                 asyncio.set_event_loop(None) # Detach the loop from the thread

        # Create and start the thread
        thread = threading.Thread(target=run_async_in_new_loop)
        thread.daemon = True
        thread.start()

    def scrape_button_click(e):
        """Handles the button click event."""
        nonlocal is_running
        if is_running: return
        is_running = True; log_output.value = ">>> Starting process..."; scrape_button.disabled = True
        progress_ring.visible = True; status_text.value = "Running..."; page.update()
        # Now start the thread *after* initial UI updates are done
        run_backend_in_thread()

    # --- Button Action ---
    scrape_button.on_click = scrape_button_click

    # --- Layout ---
    page.add(
        ft.Row( [subreddit_input, scrape_button, progress_ring, ft.Text("Status:"), status_text],
            alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=15 ),
        ft.Divider(height=10),
        ft.Container( content=log_output, expand=True, padding=ft.padding.only(top=5) ) )
    page.update()

# --- Run the Flet App ---
if __name__ == "__main__":
    print("Starting Reddit Scraper Flet application (ADK Version)...")
    if not os.path.exists(OUTPUT_DIRECTORY):
        try: os.makedirs(OUTPUT_DIRECTORY); print(f"Created output directory: {OUTPUT_DIRECTORY}")
        except OSError as e: print(f"Error creating output directory '{OUTPUT_DIRECTORY}': {e}")

    print("Ensure required libraries are installed:")
    print("  pip install flet praw python-dotenv google-adk")
    print("Ensure Reddit API credentials and Google API Key are set in a '.env' file in the project root.")

    ft.app(target=main) # view=ft.AppView.FLET_APP (Optional for desktop look)