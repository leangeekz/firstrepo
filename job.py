
import pymongo
from pymongo.errors import BulkWriteError
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime

def get_id_ranges(source_collection, num_ranges):
    """
    Divide the collection into ranges based on the ObjectId generation time.
    """
    first_id = source_collection.find_one(sort=[("_id", 1)])["_id"]
    last_id = source_collection.find_one(sort=[("_id", -1)])["_id"]

    first_timestamp = first_id.generation_time
    last_timestamp = last_id.generation_time

    # Calculate the time interval for each range
    total_seconds = int((last_timestamp - first_timestamp).total_seconds())
    seconds_per_range = total_seconds // num_ranges

    ranges = []
    for i in range(num_ranges):
        start_time = first_timestamp + datetime.timedelta(seconds=i * seconds_per_range)
        end_time = first_timestamp + datetime.timedelta(seconds=(i + 1) * seconds_per_range)

        # Convert times back to ObjectId
        start_id = ObjectId.from_datetime(start_time)
        end_id = ObjectId.from_datetime(end_time)

        ranges.append((start_id, end_id))

    # Adjust the last range to include the last_id
    ranges[-1] = (ranges[-1][0], last_id)
    return ranges


def process_range(start_id, end_id, source_collection, target_collection, job_id, import_job_collection):
    """
    Process a range of documents from the source collection and write them to the target collection.
    """
    bulk_operations = []
    count = 0
    for item in source_collection.find({"_id": {"$gte": start_id, "$lt": end_id}}):
        # ... (same processing logic as before)
        count += 1

    if bulk_operations:
        try:
            result = target_collection.bulk_write(bulk_operations, ordered=False)
            import_job_collection.update_one(
                {'_id': job_id},
                {'$inc': {'total_records_processed': result.bulk_api_result['nModified']}}
            )
        except BulkWriteError as bwe:
            print("Bulk write error:", bwe.details)
            import_job_collection.update_one(
                {'_id': job_id},
                {'$set': {'status': 'Failed', 'error_details': str(bwe.details)}}
            )
        except Exception as e:
            print("An error occurred:", e)
            import_job_collection.update_one(
                {'_id': job_id},
                {'$set': {'status': 'Failed', 'error_details': str(e)}}
            )

    return count

def get_id_ranges(source_collection, chunk_size):
    """
    Divide the collection into ranges based on the _id field, with each range
    approximately covering 'chunk_size' documents.
    """
    total_docs = source_collection.estimated_document_count()
    num_ranges = (total_docs + chunk_size - 1) // chunk_size  # Ceiling division

    min_id = source_collection.find_one(sort=[("_id", 1)])["_id"]
    max_id = source_collection.find_one(sort=[("_id", -1)])["_id"]

    interval = (max_id - min_id) // num_ranges
    ranges = [(min_id + interval * i, min_id + interval * (i + 1)) for i in range(num_ranges)]
    ranges[-1] = (ranges[-1][0], max_id)  # Ensure the last range goes up to the max_id
    return ranges

def initialize_job_log(import_job_collection, collection_name):
    """
    Initialize a log entry for a new job.
    """
    return import_job_collection.insert_one({
        'job_name': 'DataMigrationJob',
        'collection_name': collection_name,
        'status': 'New',
        'total_records_processed': 0,
        'start_date': datetime.datetime.now(),
        'end_date': None,
        'last_updated': datetime.datetime.now()
    }).inserted_id

def update_job_status(import_job_collection, job_id, status):
    """
    Update the job status.
    """
    import_job_collection.update_one(
        {'_id': job_id},
        {'$set': {'status': status, 'last_updated': datetime.datetime.now()}}
    )

def main():
    source_mongo_params = {'host': 'source_host'}
    target_mongo_params = {'host': 'target_host'}

    source_client = pymongo.MongoClient(**source_mongo_params)
    target_client = pymongo.MongoClient(**target_mongo_params)

    source_db = source_client['source_db']
    target_db = target_client['target_db']
    import_job_collection = target_db['import_job']

    chunk_size = 100000  # Define your chunk size here

    for collection_name in source_db.list_collection_names():
        job_id = initialize_job_log(import_job_collection, collection_name)
        update_job_status(import_job_collection, job_id, 'In Progress')

        source_collection = source_db[collection_name]
        target_collection = target_db['target_collection']

        id_ranges = get_id_ranges(source_collection, chunk_size)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_range, start_id, end_id, source_collection, target_collection, job_id, import_job_collection) for start_id, end_id in id_ranges]
            for future in as_completed(futures):
                pass  # Future results can be processed here if needed

        update_job_status(import_job_collection, job_id, 'Completed')

    source_client.close()
    target_client.close()

if __name__ == "__main__":
    main()
