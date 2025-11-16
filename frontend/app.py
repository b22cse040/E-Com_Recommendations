import os
import json
import threading
import redis
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, session
from sentence_transformers import SentenceTransformer
from saved_crossencoder.FT_Ranker import load_ranker_model

# Custom modules
from src.speech import fetch_query_by_voice
from frontend.logic import process_main_query, save_logs
from src.DB.logging_interaction import actions_collection
from src.DB.auth import create_user, authenticate_user, update_user_likes
from src.DB.auth_cache import cache_user, get_cached_user, update_cached_user

load_dotenv()

# Flask setup
app = Flask(__name__, static_url_path='/static')
app.secret_key = "super_secret_key_please_change"    # IMPORTANT: change in production

# Redis setup
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT_NO")),
    db=int(os.getenv("REDIS_DB"))
)

# Models
model_name = os.getenv("MODEL_NAME")
embedder = SentenceTransformer(os.getenv("EMBEDDING_MODEL_NAME"))
model, tokenizer = load_ranker_model(r"../saved_crossencoder")


# -------------------------------------------------------
# AUTH ROUTES
# -------------------------------------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        age = int(request.form.get("age"))
        gender = request.form.get("gender")

        success, msg = create_user(username, password, age, gender)
        if success:
            return redirect("/login")
        return render_template("signup.html", error=msg)

    return render_template("signup.html")


# @app.route("/login", methods=["GET", "POST"])
# def login():
#     if request.method == "POST":
#         username = request.form.get("username")
#         password = request.form.get("password")
#
#         success, user = authenticate_user(username, password)
#
#         if success:
#             session["username"] = user["username"]
#             return redirect("/")
#
#         return render_template("login.html", error=user)
#
#     return render_template("login.html")
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        success, user = authenticate_user(username, password)

        if success:
            # ---- Cache user in Redis ----
            cache_user(redis_client, {
                "username": user["username"],
                "age": user["age"],
                "gender": user["gender"],
                "previous_liked": user["previous_liked"],
                "previous_disliked": user["previous_disliked"]
            })

            session["username"] = user["username"]
            return redirect("/")

        return render_template("login.html", error=user)

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect("/login")


# -------------------------------------------------------
# ROOT SEARCH PAGE
# -------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if "username" not in session:
        return redirect("/login")

    if request.method == "POST":
        use_voice = request.form.get("use_voice", "false").lower() == "true"

        if use_voice:
            user_query = fetch_query_by_voice()
        else:
            user_query = request.form.get("query", "").strip()

        if not user_query:
            return render_template("error.html", message="Please enter a query.")

        try:
            # ---------------------------------------------
            # FETCH USER METADATA FOR PERSONALIZATION
            # ---------------------------------------------
            from src.DB.logging_interaction import users_collection

            user_doc = users_collection.find_one({"username": session["username"]})

            metadata = {
                "age": user_doc.get("age"),
                "gender": user_doc.get("gender"),
                "previous_liked": user_doc.get("previous_liked", []),
                "previous_disliked": user_doc.get("previous_disliked", [])
            }

            # ---------------------------------------------
            # RUN MAIN QUERY WITH METADATA INCLUDED
            # ---------------------------------------------
            results, main_logs = process_main_query(
                user_query,
                model_name,
                ranker_model=model,
                tokenizer=tokenizer,
                embedder=embedder,
                device="cpu",
                redis_client=redis_client,
                user_metadata=metadata     # <-- IMPORTANT
            )

            save_logs(user_query, main_logs)

            return render_template(
                "result2.html",
                user_query=user_query,
                results=results
            )

        except Exception as e:
            return render_template("error.html", message=str(e))

    return render_template("index.html")


# -------------------------------------------------------
# PRODUCT ACTION API
# -------------------------------------------------------
@app.route("/product-action", methods=["POST"])
def product_action():
    if "username" not in session:
        return jsonify({"status": "error", "message": "Not logged in"}), 401

    data = request.get_json()
    product_name = data["product"]
    action = data["action"]
    query = data.get("query", "unknown")

    if not product_name or not action:
        return jsonify({"status": "error", "message": "Missing fields"}), 400

    username = session["username"]

    # ---- Redis updates ----
    if action == "AddToCart":
        redis_client.rpush("cart:"+username, product_name)
        message = f"Added {product_name} to cart."

    elif action == "RemoveFromCart":
        redis_client.lrem("cart:"+username, 0, product_name)
        message = f"Removed {product_name} from cart."

    elif action == "Like":
        redis_client.rpush("liked:"+username, product_name)
        message = f"You liked {product_name}."
        label = 1

    elif action == "Dislike":
        redis_client.rpush("disliked:"+username, product_name)
        message = f"You disliked {product_name}."
        label = 0

    else:
        return jsonify({"status": "error", "message": "Invalid action"}), 400

    # ---- MongoDB logging ----
    if action in ["Like", "Dislike"]:
        try:
            actions_collection.insert_one({
                "username": username,
                "query": query,
                "product_info": product_name,
                "label": label
            })

            update_user_likes(
                username=username,
                product_name=product_name,
                like=(label == 1)
            )

            # ---- Update Redis cached user preferences ----
            cached = get_cached_user(redis_client, username)
            if cached:
                if label == 1:
                    cached["previous_liked"].append(product_name)
                else:
                    cached["previous_disliked"].append(product_name)

                cache_user(redis_client, cached)

        except Exception as e:
            print(f"Mongo Failed: {str(e)}")

    return jsonify({"status": "success", "message": message})


# -------------------------------------------------------
# VIEW USER ACTIVITY
# -------------------------------------------------------
@app.route("/view-activity")
def view_activity():
    if "username" not in session:
        return redirect("/login")

    username = session["username"]

    cart_items = redis_client.lrange("cart:"+username, 0, -1)
    liked_items = redis_client.lrange("liked:"+username, 0, -1)
    disliked_items = redis_client.lrange("disliked:"+username, 0, -1)

    cart_items = [item.decode() for item in cart_items]
    liked_items = [item.decode() for item in liked_items]
    disliked_items = [item.decode() for item in disliked_items]

    return render_template(
        "activity.html",
        cart=cart_items,
        liked=liked_items,
        dislikes=disliked_items
    )


# -------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
