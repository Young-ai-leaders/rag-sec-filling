from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI"))

db = client["sec_filing"]
collection = db["embedded_chunks"]

print("Document count:", collection.count_documents({}))
