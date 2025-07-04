import os, json, re
import streamlit as st
from dotenv import load_dotenv
from src.llms.llms import form_response

load_dotenv()
model_name = os.getenv('MODEL_NAME')

# --------------------------- Streamlit UI Setup --------------------
st.set_page_config(page_title="Interior Designer Product Search", page_icon="🛋️")
st.title("Interior Designer Product Search & Recommendation Chatbot")

if "messages" not in st.session_state:
  st.session_state.messages = []

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