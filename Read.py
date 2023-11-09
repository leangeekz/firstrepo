def fetch_data_in_range(collection, start_id, end_id):
    # Assuming collection is a pymongo collection instance
    batch_size = 1000  # Define the batch size for each query
    last_id = start_id
    
    while last_id < end_id:
        # Fetch a batch of documents within the range
        cursor = collection.find(
            {'_id': {'$gt': last_id, '$lte': end_id}},
            batch_size=batch_size
        ).sort('_id', 1)  # Make sure to sort by '_id' to maintain order

        # Process documents in the current batch
        for document in cursor:
            # Process your document here
            # process_document(document)
            print(document)  # Example action, replace with actual processing
            last_id = document['_id']  # Update the last_id to the last processed document's '_id'

        # Break the loop if we didn't get a full batch indicating we have processed all available documents
        if cursor.retrieved < batch_size:
            break

# Example usage of the function
source_db = MongoClient('mongodb://source_server')['source_database']
collection = source_db['large_collection']
ranges = get_id_ranges_for_chunks('large_collection', 10)

for start_id, end_id in ranges:
    fetch_data_in_range(collection, start_id, end_id)
