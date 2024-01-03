from pymongo import MongoClient
import threading

# Constants - replace with your actual values
MONGO_URI = 'mongodb://localhost:27017'  # MongoDB URI
DB_NAME = 'myDatabase'  # Your database name
COLLECTION_NAME = 'myCollection'  # Your collection name

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# Get min and max _id values
min_id = collection.find_one(sort=[("_id", 1)])["_id"]
max_id = collection.find_one(sort=[("_id", -1)])["_id"]

def update_records(start_id, end_id):
    """
    Update records in the specified _id range.
    """
    for doc in collection.find({"_id": {"$gte": start_id, "$lt": end_id}}):
        # Update operation - Modify according to your update criteria
        collection.update_one({"_id": doc["_id"]}, {"$set": {"updated": True}})
        print(f"Updated _id: {doc['_id']}")

def divide_work(min_id, max_id, num_threads):
    """
    Divide the work among threads based on _id range.
    """
    range_size = (max_id - min_id) // num_threads
    threads = []

    for i in range(num_threads):
        # Calculate start and end _ids for each thread
        start_id = min_id + i * range_size
        end_id = start_id + range_size if i < num_threads - 1 else max_id + 1

        # Create and start a thread
        thread = threading.Thread(target=update_records, args=(start_id, end_id))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

# Number of threads you want to use
num_threads = 10  # Adjust this to your needs

# Start the threading process
divide_work(min_id, max_id, num_threads)
