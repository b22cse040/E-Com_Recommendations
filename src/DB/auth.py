import bcrypt
from src.DB.logging_interaction import users_collection

def create_user(username, password, age, gender):
    if users_collection.find_one({"username": username}):
        return False, "User already exists"

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    user_doc = {
        "username": username,
        "password": hashed,
        "age": age,
        "gender": gender,
        "previous_liked": [],
        "previous_disliked": []
    }

    users_collection.insert_one(user_doc)
    return True, "User registered successfully"


def authenticate_user(username, password):
    user = users_collection.find_one({"username": username})
    if not user:
        return False, "User not found"

    if bcrypt.checkpw(password.encode(), user["password"]):
        return True, user

    return False, "Incorrect password"


def update_user_likes(username, product_name, like=True):
    if like:
        users_collection.update_one(
            {"username": username},
            {"$push": {"previous_liked": product_name}}
        )
    else:
        users_collection.update_one(
            {"username": username},
            {"$push": {"previous_disliked": product_name}}
        )