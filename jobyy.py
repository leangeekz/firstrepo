import threading
from pymongo import MongoClient

# Parameters
db_name = 'your_db'
my_collection_name = 'my_collection'
source_collection_name = 'source_collection'
num_threads = 10  # Adjust based on your machine's capability and network

# MongoDB connection setup
client = MongoClient('mongodb://localhost:27017/')
db = client[db_name]
my_collection = db[my_collection_name]
source_collection = db[source_collection_name]

# Function to update documents
def update_documents(batch):
    for doc in batch:
        # Query the source collection
        source_doc = source_collection.find_one({"account_number": doc["account_number"]})
        
        # Define the update operation here, for example:
        # update_query = {"$set": {"new_field": source_doc["some_field"]}}
        
        # Update the document in my_collection
        my_collection.update_one({'_id': doc['_id']}, update_query)

# Prepare and execute threads for each batch
batch_size = 1000  # Adjust based on your preference and performance considerations
cursor = my_collection.find({}, {'_id': 1, 'account_number': 1}).batch_size(batch_size)

# List to keep track of threads
threads = []

# Create and start a new thread for each batch
for batch in cursor:
    current_batch = [doc for doc in batch]
    if current_batch:
        thread = threading.Thread(target=update_documents, args=(current_batch,))
        thread.start()
        threads.append(thread)

        # Optional: Limit the number of concurrent threads to num_threads
        if len(threads) >= num_threads:
            for t in threads:
                t.join()  # Wait for all the threads in the list to finish
            threads = []  # Clear the list for the next set of threads

# Wait for the remaining threads to complete
for thread in threads:
    thread.join()

print("Update operation completed.")
