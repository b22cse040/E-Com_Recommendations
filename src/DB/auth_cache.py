import json

def cache_user(redis_client, user):
    """
    Cache user data in redis for fast access.
    Key: user:{username}
    """
    key = f"user:{user['username']}"
    redis_client.set(key, json.dumps(user))


def get_cached_user(redis_client, username):
    """
    Return cached user data if exists.
    Else return None.
    """
    key = f"user:{username}"
    data = redis_client.get(key)
    if data:
        return json.loads(data)
    return None


def update_cached_user(redis_client, username, field, value):
    """
    Update a single field in user cache.
    """
    key = f"user:{username}"
    data = redis_client.get(key)

    if not data:
        return  # nothing to update

    user = json.loads(data)
    user[field] = value
    redis_client.set(key, json.dumps(user))