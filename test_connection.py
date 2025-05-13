from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

try:
    # Connect using environment variables
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client[os.getenv("DB_NAME")]
    collection = db[os.getenv("COLLECTION_NAME")]

    # Test connection
    print("Connection successful! Server info:")
    print(client.server_info())

    # Document count verification
    print("\nDocument count:", collection.count_documents({}))

except Exception as e:
    print(f"Connection failed: {e}")