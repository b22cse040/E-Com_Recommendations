import os, json, time, threading
import streamlit as st
from dotenv import load_dotenv
from src.llms.llms import form_response
from src.query_emb import search_similar_queries

load_dotenv()
model_name = os.getenv('MODEL_NAME')

# --------------------------- Streamlit UI Setup --------------------
st.set_page_config(page_title="Interior Designer Product Search", page_icon="🛋️")
st.title("Interior Designer Product Search & Recommendation Chatbot")

if "messages" not in st.session_state:
  st.session_state.messages = []

if "similar_response" not in st.session_state:
  st.session_state["similar_response"] = {}

if "similar_queries" not in st.session_state:
  st.session_state["similar_queries"] = []

if "active_similar_query" not in st.session_state:
  st.session_state["active_similar_query"] = None

if "new_query" not in st.session_state:
  st.session_state["new_query"] = False

for msg in st.session_state.messages:
  with st.chat_message(msg["role"]):
    st.markdown(msg["content"])

# ----------------------- Main query handling ---------------------------------
user_input = st.text_input("Type your query about furniture, decor, etc.")

# Only set the new_query flag if input is freshly typed by user
if user_input and not st.session_state["active_similar_query"]:
  st.session_state["new_query"] = True

# ---------------------- Similar queries loader thread ------------------------
similar_results_holder = {}
def load_similar_queries(main_query: str, model_name: str, holder_dict: dict, log_lines: list) -> None:
  '''
  The main logic behind this is while the user reads the results of the query input,
  in tha background another thread will process similar queries based on "query" type
  in elasticsearch.
  '''
  start_time = time.time()
  similar_queries = search_similar_queries(main_query)
  similar_queries_time = time.time() - start_time
  log_lines.append(f"Similar query search time: {similar_queries_time:.4f} sec")

  similar_responses = {}
  for sim_query in similar_queries:
    sim_raw_json_str = form_response(sim_query, model_name)
    sim_results = json.loads(sim_raw_json_str)
    similar_responses[sim_query] = sim_results
    print(sim_query, '\n')
  form_sim_time = time.time() - start_time
  log_lines.append(f"Similar query response time: {form_sim_time:.4f} sec")
  ## Streamlit doesn't give access to context outside main thread so creating a
  ## holding_dict to hold the results temporarily
  holder_dict["similar_queries"] = similar_queries
  holder_dict["similar_response"] = similar_responses

if st.session_state["new_query"]:
  log_lines = []
  st.session_state.messages.append({
    "role" : "user",
    "content" : user_input,
  })

  with st.chat_message(user_input):
    st.markdown(user_input)

  with st.spinner("Thinking..."):
    try:
      start_main = time.time()
      # Fetching result for the main query
      raw_json_str = form_response(user_input, model_name)
      results = json.loads(raw_json_str)
      log_lines.append(f"Main query response time: {time.time() - start_main:.4f} sec")

      # Fetching results for the similar queries in a different thread
      start_sim = time.time()
      sim_thread = threading.Thread(
        target=load_similar_queries,
        args=(user_input, model_name, similar_results_holder, log_lines),
      )
      sim_thread.start()

      # Joining the threads so as to access resources from the subsidiary thread
      sim_thread.join()
      sim_total_time = time.time() - start_sim
      log_lines.append(f"Similar queries thread time: {sim_total_time:.4f} sec")

      ## Adding result to session_state
      st.session_state["similar_queries"] = similar_results_holder["similar_queries"]
      st.session_state["similar_response"] = similar_results_holder["similar_response"]

    except Exception as e:
      results = {}
      st.error(f"An error occurred: {e}")

  if not results:
    bot_reply = "No valid products found for your query. Please try again."
  else:
    formatted = ""
    for obj_key, obj_val in results.items():
      formatted += f"### {obj_val['Name']}\n"
      formatted += f"- **Why?** {obj_val['Explanation']}\n\n"
    bot_reply = formatted

  st.session_state.messages.append({
    "role" : "bot",
    "content" : bot_reply,
  })

  with st.chat_message("bot"):
    st.markdown(bot_reply, unsafe_allow_html=True)

  filepath = r"D:\Sparkathon\evals\frontend_time.txt"
  with open(filepath, "a") as f:
    f.write(f"Query: {user_input}\n")
    for line in log_lines:
      f.write(line + "\n")
    f.write("----\n")

  st.session_state["new_query"] = False

# ------------------------ Similar Queries Buttons -----------------------------
if st.session_state["similar_queries"]:
  st.markdown("### Users also searched for: ")
  for sim_query in st.session_state["similar_queries"]:
    if st.button(sim_query):
      st.session_state["similar_queries"].remove(sim_query)

if st.session_state["active_similar_query"]:
  active_query = st.session_state["active_similar_query"]
  active_responses = st.session_state["similar_response"].get(active_query, {})

  if not active_responses:
    st.markdown("no active products found for your query. Please try rephrasing")

  else:
    st.markdown(f'## Results for: {active_query}')
    formatted = ""
    for obj_key, obj_val in active_responses.items():
      formatted += f"### {obj_val['Name']}\n"
      formatted += f"- **Why?** {obj_val['Explanation']}\n"
    st.markdown(formatted, unsafe_allow_html=True)