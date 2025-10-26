import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
mongo_uri = os.getenv("MONGO_URI")
mongo_db_action = os.getenv("MONGO_DB_ACTION")

mongo_client = MongoClient(mongo_uri)
mongo_action_db = mongo_client[mongo_db_action]
actions_collection = mongo_action_db["actions"]

