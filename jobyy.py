from pymongo import MongoClient
import threading

# Constants - replace with your actual values
MONGO_URI = 'mongodb://localhost:27017'  # MongoDB URI
DB_NAME = 'myDatabase'  # Your database name
COLLECTION_NAME = 'myCollection'  # Your collection name

# Min and Max account numbers
min_account_number = 12345
max_account_number = 99939506852

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

def update_records(start, end):
    """
    Update records in the specified range.
    """
    for account_number in range(start, end):
        # Update operation - Modify according to your update criteria
        collection.update_one({"account_number": account_number}, {"$set": {"updated": True}})
        print(f"Updated account number: {account_number}")

def divide_work(min_val, max_val, num_threads):
    """
    Divide the work among threads.
    """
    range_size = (max_val - min_val) // num_threads
    threads = []

    for i in range(num_threads):
        # Calculate start and end points for each thread
        start = min_val + i * range_size
        end = start + range_size if i < num_threads - 1 else max_val + 1

        # Create and start a thread
        thread = threading.Thread(target=update_records, args=(start, end))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

# Number of threads you want to use
num_threads = 10  # Adjust this to your needs

# Start the threading process
divide_work(min_account_number, max_account_number, num_threads)
