import os, sys
from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.append(os.path.abspath("src"))

load_dotenv()
client = MongoClient(os.getenv("MONGODB_URI"))
col = client[os.getenv("DB_NAME")][os.getenv("COLLECTION_NAME", "embedded_chunks")]
for idx in col.aggregate([{ "$listSearchIndexes": {} }]):
    print(idx.get("name"), idx.get("type"), idx.get("latestDefinition", {}))