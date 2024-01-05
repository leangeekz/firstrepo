import threading
from pymongo import MongoClient
from queue import Queue

# Parameters
db_name = 'your_db'
collection_name = 'pipeline_collection'
num_threads = 10  # Adjust based on your machine's capability and network

# MongoDB connection setup
client = MongoClient('mongodb://localhost:27017/')
db = client[db_name]
collection = db[collection_name]

# Queue to hold the batches of _ids to update
id_queue = Queue()

# Function to update documents
def update_documents():
    while not id_queue.empty():
        # Get a batch of _ids from the queue
        batch = id_queue.get()
        
        # Define the update operation here, for example:
        # update_query = {"$set": {"new_field": "new_value"}}
        
        # Update the documents in MongoDB
        for _id in batch:
            collection.update_one({'_id': _id}, update_query)
        
        # Indicate the task is done
        id_queue.task_done()

# Fill the queue with batches of _ids
batch_size = 1000  # Adjust based on your preference and performance considerations
cursor = collection.find({}, {'_id': 1}).batch_size(batch_size)
current_batch = []

for document in cursor:
    current_batch.append(document['_id'])
    if len(current_batch) >= batch_size:
        id_queue.put(current_batch)
        current_batch = []

# Add any remaining _ids
if current_batch:
    id_queue.put(current_batch)

# Create and start threads
threads = []
for i in range(num_threads):
    thread = threading.Thread(target=update_documents)
    thread.start()
    threads.append(thread)

# Wait for all threads to complete
for thread in threads:
    thread.join()

print("Update operation completed.")
