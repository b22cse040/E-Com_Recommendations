import os
import json
import time
import threading
import streamlit as st
from dotenv import load_dotenv
from src.llms import form_response
from src.query_emb import search_similar_queries

load_dotenv()
model_name = os.getenv('MODEL_NAME')

# --------------------------- Streamlit Setup --------------------
st.set_page_config(page_title="Interior Designer Product Search", page_icon="🛋️")
st.title("Interior Designer Product Search & Recommendation Chatbot")

# --------------------------- Session State Init -----------------
if "messages" not in st.session_state:
  st.session_state["messages"] = []

if "similar_response" not in st.session_state:
  st.session_state["similar_response"] = {}

if "similar_queries" not in st.session_state:
  st.session_state["similar_queries"] = []

if "active_similar_query" not in st.session_state:
  st.session_state["active_similar_query"] = None

if "main_query_done" not in st.session_state:
  st.session_state["main_query_done"] = False

# Display previous messages
for msg in st.session_state["messages"]:
  with st.chat_message(msg["role"]):
    st.markdown(msg["content"])

# --------------------------- Logic Functions --------------------
def process_main_query(query, model_name):
  logs = []
  start_time = time.time()
  raw_json_str = form_response(query, model_name)
  results = json.loads(raw_json_str)
  logs.append(f"Main query response time: {time.time() - start_time:.4f} sec")
  return results, logs

def fetch_similar_queries(query, model_name):
  logs = []
  start_time = time.time()

  similar_queries = search_similar_queries(query)
  logs.append(f"Similar query search time: {time.time() - start_time:.4f} sec")

  similar_responses = {}
  for sim_query in similar_queries:
    t0 = time.time()
    sim_raw_json_str = form_response(sim_query, model_name)
    sim_results = json.loads(sim_raw_json_str)
    similar_responses[sim_query] = sim_results
    logs.append(f"Similar query '{sim_query}' response time: {time.time() - t0:.4f} sec")

  logs.append(f"Total similar queries time: {time.time() - start_time:.4f} sec")
  return similar_queries, similar_responses, logs

def save_logs(query, logs, filepath=r"D:\Sparkathon\evals\frontend_time.txt"):
  with open(filepath, "a") as f:
    f.write(f"Query: {query}\n")
    for line in logs:
      f.write(line + "\n")
    f.write("----\n")

# --------------------------- Main Query Block -------------------
user_input = st.text_input("Type your query about furniture, decor, etc.", key="user_query")

if user_input and not st.session_state["main_query_done"]:
  st.session_state["active_similar_query"] = None

  st.session_state.messages.append({"role": "user", "content": user_input})
  with st.chat_message("user"):
    st.markdown(user_input)

  with st.spinner("Thinking..."):
    try:
      # Main query results
      results, main_logs = process_main_query(user_input, model_name)

      # Similar queries (background thread, but we wait since you want them pre-cached before button click)
      holder_dict = {}
      def background_fetch():
        similar_queries, similar_responses, sim_logs = fetch_similar_queries(user_input, model_name)
        holder_dict["similar_queries"] = similar_queries
        holder_dict["similar_response"] = similar_responses
        holder_dict["logs"] = sim_logs

      sim_thread = threading.Thread(target=background_fetch)
      sim_thread.start()
      sim_thread.join()

      st.session_state["similar_queries"] = holder_dict["similar_queries"]
      st.session_state["similar_response"] = holder_dict["similar_response"]

      # Combine logs
      full_logs = main_logs + holder_dict["logs"]
      save_logs(user_input, full_logs)

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

  st.session_state.messages.append({"role": "bot", "content": bot_reply})
  with st.chat_message("bot"):
    st.markdown(bot_reply, unsafe_allow_html=True)

  st.session_state["main_query_done"] = True

# --------------------------- Similar Query Buttons -----------------
if st.session_state["similar_queries"]:
  st.markdown("### Users also searched for:")
  for sim_query in st.session_state["similar_queries"]:
    if st.button(sim_query):
      st.session_state["active_similar_query"] = sim_query

# --------------------------- Show Similar Query Results -------------
if st.session_state["active_similar_query"]:
  active_query = st.session_state["active_similar_query"]
  active_responses = st.session_state["similar_response"].get(active_query, {})

  if not active_responses:
    st.markdown("No active products found for your query. Please try rephrasing.")
  else:
    st.markdown(f'## Results for: **{active_query}**')
    formatted = ""
    for obj_key, obj_val in active_responses.items():
      formatted += f"### {obj_val['Name']}\n"
      formatted += f"- **Why?** {obj_val['Explanation']}\n\n"
    st.markdown(formatted, unsafe_allow_html=True)