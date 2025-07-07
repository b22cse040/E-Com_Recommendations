import os
import json
import time
import threading
import streamlit as st
from dotenv import load_dotenv
from src.llms.llms import form_response
from src.query_emb import search_similar_queries
from src.utils.logger import logger

# Load environment variables from .env file
load_dotenv()
model_name = os.getenv('MODEL_NAME')

# --------------------------- Streamlit Page Setup --------------------
st.set_page_config(
    page_title="Interior Designer Product Search", page_icon="🛋️")
st.title("Interior Designer Product Search & Recommendation Chatbot")

# --------------------------- Session State Initialization -----------------
# Initialize all necessary keys in the session state to prevent errors.
if "messages" not in st.session_state:
  st.session_state["messages"] = []

if "similar_response" not in st.session_state:
  st.session_state["similar_response"] = {}

if "similar_queries" not in st.session_state:
  st.session_state["similar_queries"] = []

if "active_similar_query" not in st.session_state:
  st.session_state["active_similar_query"] = None

# New flags to manage the asynchronous-like behavior
if "main_query_done" not in st.session_state:
  st.session_state["main_query_done"] = False

if "sim_queries_started" not in st.session_state:
  st.session_state["sim_queries_started"] = False

if "sim_queries_done" not in st.session_state:
  st.session_state["sim_queries_done"] = False

# Display previous chat messages from the history
for msg in st.session_state["messages"]:
  with st.chat_message(msg["role"]):
    st.markdown(msg["content"], unsafe_allow_html=True)

# --------------------------- Core Logic Functions --------------------


def process_main_query(query, model_name):
  """Processes the user's primary query and returns formatted results."""
  logger.info(f"Processing main query: '{query}'")
  start_time = time.time()
  raw_json_str = form_response(query, model_name)
  results = json.loads(raw_json_str)
  logger.info(
      f"Main query processing took: {time.time() - start_time:.2f} sec")
  return results


def fetch_and_cache_similar_queries(query, model_name):
  """
  This function runs in a background thread to find similar queries
  and pre-generate their responses, caching them in the session state.
  """
  logger.info("Background thread started for similar queries.")
  start_time = time.time()

  try:
    # 1. Find semantically similar queries
    similar_queries = search_similar_queries(query)
    similar_responses = {}

    # 2. For each similar query, generate and store the full response
    for sim_query in similar_queries:
        sim_raw_json_str = form_response(sim_query, model_name)
        sim_results = json.loads(sim_raw_json_str)
        similar_responses[sim_query] = sim_results

    # 3. Update session state from the background thread
    st.session_state["similar_queries"] = similar_queries
    st.session_state["similar_response"] = similar_responses

  except Exception as e:
    logger.error(f"Error in background thread for similar queries: {e}")
    # Clear to avoid showing stale data
    st.session_state["similar_queries"] = []

  finally:
    # 4. Signal that the background work is complete
    st.session_state["sim_queries_done"] = True
    logger.info(
        f"Background thread finished in {time.time() - start_time:.2f} sec.")


# --------------------------- Main Interaction Block -------------------
user_input = st.text_input(
    "Type your query about furniture, decor, etc.", key="user_query")

# This block executes only once when a new query is submitted
if user_input and not st.session_state["main_query_done"]:
  # Reset state for the new query
  st.session_state["active_similar_query"] = None
  st.session_state["sim_queries_started"] = False
  st.session_state["sim_queries_done"] = False
  st.session_state["similar_queries"] = []
  st.session_state["similar_response"] = {}
  st.session_state["messages"] = []  # Clear previous chat for new interaction

  # Display user's message
  st.session_state.messages.append({"role": "user", "content": user_input})
  with st.chat_message("user"):
    st.markdown(user_input)

  # --- STEP 1: Process Main Query and Display Immediately ---
  with st.spinner("Thinking..."):
    try:
      results = process_main_query(user_input, model_name)
      if not results:
        bot_reply = "No valid products found for your query. Please try again."
      else:
        # Format the main response for display
        formatted_response = ""
        for obj_key, obj_val in results.items():
          formatted_response += f"### {obj_val['Name']}\n"
          formatted_response += f"- **Why?** {obj_val['Explanation']}\n\n"
        bot_reply = formatted_response

      # Display bot's response and save to history
      st.session_state.messages.append({"role": "bot", "content": bot_reply})
      with st.chat_message("bot"):
        st.markdown(bot_reply, unsafe_allow_html=True)

      # Mark the main query as done to prevent re-running
      st.session_state["main_query_done"] = True

    except Exception as e:
      logger.error(
          f"An error occurred during main query processing: {e}", exc_info=True)
      st.error(f"An error occurred while fetching your results: {e}")

  # --- STEP 2: Start Background Thread for Similar Queries ---
  # This runs only after the main query is successfully displayed
  if st.session_state["main_query_done"]:
    st.session_state["sim_queries_started"] = True
    sim_thread = threading.Thread(
        target=fetch_and_cache_similar_queries,
        args=(user_input, model_name),
        daemon=True  # Ensure thread exits when main app exits
    )
    sim_thread.start()
    # **REMOVED sim_thread.join()** to make the UI non-blocking

# --------------------------- Similar Queries Display Section -----------------
# This section handles displaying the "Users also searched for" buttons
if st.session_state["sim_queries_started"]:
  # If background job is not done, show a spinner and force UI to check again
  if not st.session_state["sim_queries_done"]:
    with st.spinner("Finding related searches..."):
        # This loop forces Streamlit to periodically check if the background job is done
        while not st.session_state["sim_queries_done"]:
            time.sleep(1)
    st.rerun()  # Rerun one last time to draw the buttons

  # Once the job is done, display the buttons if any were found
  if st.session_state["sim_queries_done"] and st.session_state["similar_queries"]:
    st.markdown("### Users also searched for:")
    for sim_query in st.session_state["similar_queries"]:
      if st.button(sim_query, key=f"btn_{sim_query}"):
        st.session_state["active_similar_query"] = sim_query
        st.rerun()  # Rerun to display the results for the clicked button

# --------------------------- Display Clicked Similar Query Results -------------
# This block shows the pre-cached results when a user clicks a "similar query" button
if st.session_state["active_similar_query"]:
  active_query = st.session_state["active_similar_query"]
  active_responses = st.session_state["similar_response"].get(active_query, {})

  st.markdown("---")  # Visual separator
  if not active_responses:
    st.markdown("No products were found for this related query.")
  else:
    st.markdown(f'## Results for: **{active_query}**')
    formatted_similar = ""
    for obj_key, obj_val in active_responses.items():
      formatted_similar += f"### {obj_val['Name']}\n"
      formatted_similar += f"- **Why?** {obj_val['Explanation']}\n\n"
    st.markdown(formatted_similar, unsafe_allow_html=True)
