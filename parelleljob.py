import threading
import queue
from pymongo import MongoClient, UpdateOne, BulkWriteError
import time

# Connection parameters for source and target MongoDB instances
source_mongo_params = {'host': 'source_host', 'port': 27017}
target_mongo_params = {'host': 'target_host', 'port': 27017}

# Queue to hold the chunk data
data_queue = queue.Queue()  # The maxsize is set to 0 for an infinite size

def producer(source_collection_name, batch_size, q):
    source_client = MongoClient(**source_mongo_params)
    db = source_client['source_database']
    collection = db[source_collection_name]

    cursor = collection.find({}, no_cursor_timeout=True)
    chunk_data = []
    for document in cursor:
        chunk_data.append(document)
        if len(chunk_data) >= batch_size:
            q.put(chunk_data)
            chunk_data = []
    
    # Put any remaining documents in the queue
    if chunk_data:
        q.put(chunk_data)

    # Signal to consumers that the producer is done
    q.put(None)
    
    cursor.close()
    source_client.close()

def consumer(target_collection_name, q):
    target_client = MongoClient(**target_mongo_params)
    target_db = target_client['target_database']
    target_collection = target_db[target_collection_name]

    while True:
        chunk_data = q.get()  # Get the chunk data from the queue
        if chunk_data is None:
            break  # Exit loop if None is received
        
        bulk_operations = []
        for item in chunk_data:
            prty_id = item['PRTY_ID']
            acct_nmbr = item["ACCT_NMBR"]
            product = item

            # Define the filter query and the update operation
            filter_query = {'PRTY_ID': prty_id}
            update_query = {
                # ... Your update query logic here
            }

            # Append the UpdateOne operation to the bulk operations list
            bulk_operations.append(UpdateOne(filter_query, update_query, upsert=True))

        # Perform the bulk write operation to MongoDB
        if bulk_operations:
            try:
                target_collection.bulk_write(bulk_operations, ordered=False)
            except BulkWriteError as bwe:
                print(bwe.details)
        
        q.task_done()

    target_client.close()

def main(source_collections, target_collection, num_producer_threads, num_consumer_threads, batch_size):
    start_time = time.time()

    # Start the producer threads
    producers = []
    for source_collection_name in source_collections:
        for _ in range(num_producer_threads):
            t = threading.Thread(target=producer, args=(source_collection_name, batch_size, data_queue))
            t.start()
            producers.append(t)
    
    # Start the consumer threads
    consumers = []
    for _ in range(num_consumer_threads):
        t = threading.Thread(target=consumer, args=(target_collection, data_queue))
        t.start()
        consumers.append(t)

    # Wait for all producer threads to finish
    for p in producers:
        p.join()

    # Wait for all items in the queue to be processed
    data_queue.join()

    # End the consumer threads
    for _ in consumers:
        data_queue.put(None)
    for c in consumers:
        c.join()

    print(f"Total time taken: {time.time() - start_time}")

if __name__ == "__main__":
    source_collections = ['source_collection1', 'source_collection2']  # List of source collection names
    target_collection = 'target_collection_name'  # Target collection name
    
    # Configuration
    num_producer_threads = 5  # Number of producer threads per source collection
    num_consumer_threads = 10  # Number of consumer threads
    batch_size = 100  # Number of documents to fetch per batch
    
    main(source_collections, target_collection, num_producer_threads, num_consumer_threads, batch_size)
