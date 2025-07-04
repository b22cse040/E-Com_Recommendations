import os, json, re
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

if "active_similar_query" not in st.session_state:
  st.session_state["active_similar_query"] = None

for msg in st.session_state.messages:
  with st.chat_message(msg["role"]):
    st.markdown(msg["content"])

# text input box
user_input = st.text_input("Type your query about furniture, decor, etc")

if user_input:
  st.session_state.messages.append({
    "role": "user",
    "content": user_input
  })

  with st.chat_message("user"):
    st.markdown(user_input)

  with st.spinner("Thinking..."):
    try:
      raw_json_str = form_response(user_input, model_name)
      results = json.loads(raw_json_str)

      similar_queries = search_similar_queries(user_input, top_k = 2)
      # print(similar_queries)
      similar_responses = {}
      for sim_query in similar_queries:
        sim_raw_json_str : str = form_response(sim_query, model_name)
        sim_results = json.loads(sim_raw_json_str)
        similar_responses[sim_query] = sim_results

      # print("=" * 70)
      # print(similar_responses)
      st.session_state["similar_queries"] = similar_queries
      st.session_state["similar_responses"] = similar_responses

    except Exception as e:
      results = {}
      st.error(f"An error occurred: {e}")


  if not results:
    bot_reply = "No valid products found for your query. Please try rephrasing!"

  else:
    formatted = ""
    for obj_key, obj_value in results.items():
      formatted += f"### {obj_value['Name']}\n"
      formatted += f"- **Why?** {obj_value['Explanation']}\n\n"

    bot_reply = formatted

  st.session_state.messages.append({
    "role": "bot",
    "content": bot_reply
  })

  with st.chat_message("bot"):
    st.markdown(bot_reply, unsafe_allow_html=True)

if "similar_queries" in st.session_state and st.session_state["similar_queries"]:
  st.markdown('### Users also searched for: ')
  for sim_query in st.session_state["similar_queries"]:
    query_text = sim_query
    if st.button(query_text):
      st.session_state["active_similar_query"] = query_text

if "active_similar_queries" in st.session_state:
  active_query = st.session_state["active_similar_queries"]
  active_responses = st.session_state["similar_responses"].get(active_query, {})

  if not active_responses:
    st.markdown("No active products found for your query. Please try rephrasing!")

  else:
    st.markdown(f'## Results for: **{active_query}**')
    formatted = ""
    for obj_key, obj_value in active_responses.items():
      formatted += f"### {obj_value['Name']}\n"
      formatted += f"- **{obj_value['Explanation']}**\n\n"
    st.markdown(formatted, unsafe_allow_html=True)