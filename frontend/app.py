import os, json, threading, redis
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from frontend.logic import process_main_query, fetch_similar_queries, save_logs
from src.speech import fetch_query_by_voice

load_dotenv()
model_name = os.getenv("MODEL_NAME")

redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")
redis_db = os.getenv("REDIS_DB")
redis_client = redis.Redis(host=redis_host, port=6379, db=0)

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
        "result2.html",
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

@app.route("/product-action", methods=["POST"])
def product_action():
  data = request.get_json()
  product_name = data["product"]
  action = data["action"]

  if not product_name or not action:
    return jsonify({
      "status" : "error",
      "message" : "Missing product or action!"
    })

  if action == "AddToCart":
    redis_client.rpush("cart", product_name)
    return jsonify({
      "status" : "success",
      "message" : f"Product {product_name} added to cart!"
    })

  elif action == "RemoveFromCart":
    redis_client.lrem("cart", 0, product_name)
    return jsonify({
      "status" : "success",
      "message" : f"Product {product_name} removed from cart!"
    })

  elif action == "Like":
    redis_client.rpush("liked", product_name)
    return jsonify({
      "status" : "success",
      "message" : f"Product {product_name} liked!"
    })

  elif action == "Dislike":
    redis_client.rpush("disliked", product_name)
    return jsonify({
      "status" : "success",
      "message" : f"Product {product_name} disliked!"
    })

  else:
    return jsonify({
      "status" : "error",
      "message" : "Invalid action!"
    }), 400

@app.route("/view-activity")
def view_activity():
  cart_items = redis_client.lrange("cart", 0, -1)
  liked_items = redis_client.lrange("liked", 0, -1)
  disliked_items = redis_client.lrange("disliked", 0, -1)

  cart_items = [item.decode("utf-8") for item in cart_items]
  liked_items = [item.decode("utf-8") for item in liked_items]
  disliked_items = [item.decode("utf-8") for item in disliked_items]

  return render_template("activity.html", cart=cart_items, liked=liked_items, dislikes=disliked_items)

if __name__ == "__main__":
  app.run(debug=True)