# backend/reddit_backend_processor.py
import asyncio
import traceback
import os
import json
import datetime

# Import ADK components with Detailed Error Logging
ADK_AVAILABLE = False # Assume not available initially
Agent, InMemorySessionService, Runner, adk_types = None, None, None, None # Initialize to None
try:
    from google.adk.agents import Agent
    from google.adk.sessions import InMemorySessionService
    from google.adk.runners import Runner
    print("DEBUG: Imported ADK Agent, Service, Runner.")
    try:
        from google.genai import types as adk_types_import
        adk_types = adk_types_import # Assign if successful
        print("DEBUG: Imported google.genai.types.")
    except ImportError as types_e:
        print(f"ERROR: Failed to import google.genai.types: {types_e}")
        # Make this critical, as it's needed for Content/Part
        raise types_e # Re-raise the specific error

    # If all imports above succeeded:
    ADK_AVAILABLE = True
    print("DEBUG: Successfully imported all required ADK components.")

except ImportError as e:
    # --- MODIFIED EXCEPTION HANDLING ---
    # Print the specific import error message and DO NOT define dummy classes
    print(f"ERROR: Failed to import one or more ADK components: {e}")
    print("       Ensure 'google-adk' and 'google-generativeai' are correctly installed.")
    # ADK_AVAILABLE remains False

# Import other backend components
try: from . import config, reddit_scraper, reddit_adk_tool, reddit_agent_config
except ImportError: import config, reddit_scraper, reddit_adk_tool, reddit_agent_config

_reddit_instance = None; _adk_runner = None; _adk_session_service = None

# (Tool Wrapper Function remains the same)
async def reddit_subreddit_scraper_tool_wrapper( subreddit_name: str, time_filter: str, limit: int ) -> dict:
    print(f"--- Tool Wrapper executing for r/{subreddit_name} ---"); time_filter = time_filter or 'week'; limit = limit or 50
    if not _reddit_instance: print("  [Wrapper Error] Global Reddit instance is not available."); return {"status": "error", "message": "Internal setup error: Reddit instance missing."}
    result = await reddit_adk_tool.reddit_subreddit_scraper_logic( subreddit_name=subreddit_name, time_filter=time_filter, limit=limit, log_callback=print, reddit_instance_internal=_reddit_instance )
    print(f"--- Tool Wrapper finished for r/{subreddit_name} ---"); return result

# (ADK Setup Function remains the same - relies on ADK_AVAILABLE check)
def _initialize_adk_components(log_callback):
    global _adk_runner, _adk_session_service, _reddit_instance
    # This check now correctly prevents proceeding if imports failed
    if not ADK_AVAILABLE: log_callback("CRITICAL ERROR: ADK libraries not installed or failed to import (check logs)."); return False
    if _adk_runner: log_callback("ADK components already initialized."); return True
    log_callback("Initializing ADK components...")
    if not _reddit_instance: log_callback("Initializing Reddit connection first..."); _reddit_instance = reddit_scraper.initialize_reddit();
    if not _reddit_instance: log_callback("ERROR: Failed to initialize Reddit connection..."); return False; log_callback("Reddit connection successful.")
    prepared_tools = [reddit_subreddit_scraper_tool_wrapper]; log_callback(f"Prepared tool for ADK: {prepared_tools[0].__name__}")
    try:
        if not config.GOOGLE_API_KEY: log_callback("CRITICAL ERROR: GOOGLE_API_KEY not configured..."); return False
        agent_model = config.ADK_MODEL_STRING;
        # Use the imported Agent class (will fail here if ADK_AVAILABLE is False, which is intended)
        scraper_agent = Agent( name=reddit_agent_config.AGENT_NAME, model=agent_model, description=reddit_agent_config.AGENT_DESCRIPTION, instruction=reddit_agent_config.AGENT_INSTRUCTION, tools=prepared_tools, );
        log_callback(f"Agent '{scraper_agent.name}' created with model '{agent_model}'.")
    except TypeError as te: log_callback(f"!!! TypeError Creating ADK Agent (Check Version): {te}"); log_callback(traceback.format_exc()); return False
    except Exception as agent_e: log_callback(f"!!! Error Creating ADK Agent: {agent_e}"); log_callback(traceback.format_exc()); return False
    _adk_session_service = InMemorySessionService(); _adk_runner = Runner( agent=scraper_agent, app_name=config.APP_NAME, session_service=_adk_session_service, ); log_callback("ADK Runner and Session Service initialized."); return True

# (Main Processing Function remains the same - relies on ADK_AVAILABLE check)
async def run_reddit_scrape_with_adk(subreddit_name: str, time_filter: str, limit: int, output_dir: str, log_callback):
    global _adk_runner, _adk_session_service
    log_callback(f"--- Starting ADK Reddit Scrape for r/{subreddit_name} ---")
    if not _adk_runner:
        if not _initialize_adk_components(log_callback): log_callback("ERROR: Failed to initialize ADK components."); return None
        if not _adk_runner: log_callback("ERROR: ADK Runner not available after initialization attempt."); return None
    session_id = f"scrape_{subreddit_name}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    try: session = _adk_session_service.create_session( app_name=config.APP_NAME, user_id=config.USER_ID, session_id=session_id )
    except Exception as session_e: log_callback(f"ERROR: Failed to create ADK session: {session_e}"); return None
    prompt_text = ( f"Please scrape the subreddit '{subreddit_name}' using the '{time_filter}' time filter and limit the results to {limit} posts. Use the available tool and report the outcome." )
    log_callback(f"Sending prompt to agent: '{prompt_text}'")
    # Check both ADK_AVAILABLE and adk_types before proceeding
    if not ADK_AVAILABLE or not adk_types: log_callback("ERROR: ADK components/types not loaded properly."); return None
    content = adk_types.Content(role='user', parts=[adk_types.Part(text=prompt_text)])
    final_agent_response_text = "Agent execution did not yield a final text response."; tool_result_data = None; tool_call_executed = False
    try:
        log_callback("Starting ADK event loop processing...")
        async for event in _adk_runner.run_async(user_id=config.USER_ID, session_id=session_id, new_message=content):
            event_attrs = dir(event); log_callback(f"DEBUG: Event: {type(event)} | Attrs: {event_attrs}")
            if hasattr(event, 'content'): log_callback(f"  DEBUG: event.content: {event.content}")
            if hasattr(event, 'tool_call') and event.tool_call: log_callback(f"  Event: Agent requesting tool: {getattr(event.tool_call, 'name', 'N/A')}")
            function_response = None # Check for function_response event
            if hasattr(event, 'content') and event.content and getattr(event.content, 'parts', None) and event.content.parts: function_response = getattr(event.content.parts[0], 'function_response', None)
            if function_response:
                 log_callback(f"  Event: Function response detected."); tool_call_executed = True
                 tool_response_content = getattr(function_response, 'response', None)
                 if isinstance(tool_response_content, dict):
                     log_callback(f"  DEBUG: Tool response data: {tool_response_content}");
                     if tool_response_content.get("status") == "success": tool_result_data = tool_response_content.get("data", []); log_callback(f"  DEBUG: Captured {len(tool_result_data)} items from tool response.")
                     else: log_callback(f"  Warning: Tool response status was not 'success': {tool_response_content.get('message')}")
                 else: log_callback(f"  Warning: Tool response content was not a dictionary: {tool_response_content}")
            if hasattr(event, 'content') and event.content and getattr(event.content, 'role', None) == 'model': # Check for final text
                log_callback("  Event: Model content received."); current_text = None
                if getattr(event.content, 'parts', None) and event.content.parts:
                    part_text = getattr(event.content.parts[0], 'text', None)
                    if part_text is not None: current_text = part_text; final_agent_response_text = current_text; log_callback(f"  DEBUG: Updated final agent response text: '{current_text[:100]}...'")
        log_callback("DEBUG: Finished iterating through ADK events."); log_callback(f"<<< Final Captured Agent Text: {final_agent_response_text}")
        if not tool_call_executed: log_callback("Error: Agent finished, but the 'function_response' event was never detected."); return None
        if tool_result_data is None: log_callback("Error: Tool execution detected, but no 'success' data was captured."); return None
        log_callback(f"Processing completed. Posts captured: {len(tool_result_data)}")
        log_callback(f"Attempting to save {len(tool_result_data)} posts to JSON..."); filepath = None
        try:
            os.makedirs(output_dir, exist_ok=True); timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{subreddit_name}_{time_filter}_{limit}posts_{timestamp}.json"; filepath = os.path.join(output_dir, filename)
            log_callback(f"Saving data to: {filepath}")
            with open(filepath, 'w', encoding='utf-8') as f: json.dump(tool_result_data, f, ensure_ascii=False, indent=4)
            log_callback(f"Successfully saved data to: {filepath}"); return filepath
        except Exception as e: log_callback(f"ERROR: Failed to save data to JSON file '{filepath}': {e}"); traceback.print_exc(); return None
    except Exception as e: log_callback(f"ERROR: Unhandled exception during ADK runner execution loop for {session_id}:"); traceback.print_exc(); return None
    finally:
        try:
            if _adk_session_service: _adk_session_service.delete_session( app_name=config.APP_NAME, user_id=config.USER_ID, session_id=session_id ); log_callback(f"ADK Session {session_id} deleted.")
        except Exception as del_e: log_callback(f"Warning: Error deleting session {session_id}: {del_e}")
        log_callback(f"--- ADK Reddit Scrape for r/{subreddit_name} Finished ---")