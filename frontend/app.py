import os, json, threading
from dotenv import load_dotenv
from flask import Flask, render_template, request
from frontend.logic import process_main_query, fetch_similar_queries, save_logs
from src.speech import fetch_query_by_voice

load_dotenv()
model_name = os.getenv("MODEL_NAME")

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
  if request.method == "POST":
    use_voice = request.form.get("use_voice", "false").lower() == "true"

    if use_voice:
      user_query = fetch_query_by_voice()
    else:
      user_query = request.form.get("query", "").strip()

    if not user_query:
      return render_template("error.html", message="Please enter a query.")

    try:
      results, main_logs = process_main_query(user_query, model_name)

      holder = {}

      def fetch_sim():
        similar_queries, similar_responses, sim_logs = fetch_similar_queries(user_query, model_name)
        holder["similar_queries"]=similar_queries
        holder["similar_responses"]=similar_responses
        holder["sim_logs"]=sim_logs

      thread = threading.Thread(target=fetch_sim)
      thread.start()
      thread.join()

      # Save logs
      full_logs = main_logs + holder["sim_logs"]
      save_logs(user_query, full_logs)

      return render_template(
        "result.html",
        user_query=user_query,
        results=results,
        similar_queries=holder["similar_queries"],
        similar_responses_json=json.dumps(holder["similar_responses"])
      )
    except Exception as e:
      return render_template("error.html", message=str(e))

  return render_template("index.html")

@app.route("/voice-capture", methods=["POST"])
def voice_capture():
  try:
    query = fetch_query_by_voice()
    return {"query" : query}
  except Exception as e:
    return {"query": f"Error: {str(e)}"}

if __name__ == "__main__":
  app.run(debug=True)