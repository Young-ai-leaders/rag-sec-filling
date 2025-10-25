import os, sys
from dotenv import load_dotenv
from pymongo import MongoClient

# allow running without setting PYTHONPATH manually
sys.path.append(os.path.abspath("src"))

load_dotenv()
client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
col = db[os.getenv("COLLECTION_NAME", "embedded_chunks")]
print("Connected to:", db.name, col.name)
print("Document count:", col.count_documents({}))