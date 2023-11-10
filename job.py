
import pymongo
from pymongo.errors import BulkWriteError
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime


def get_id_ranges(source_collection, num_ranges, field_name='seq_no'):
    # Get the total number of documents to estimate the average range size
    total_docs = source_collection.estimated_document_count()
    avg_range_size = total_docs // num_ranges

    ranges = []
    last_max_seq_no = None

    for _ in range(num_ranges):
        query = {}
        if last_max_seq_no is not None:
            query[field_name] = {"$gt": last_max_seq_no}

        subrange = source_collection.find(query).sort(field_name, 1).limit(avg_range_size)
        subrange_seq_nos = [doc[field_name] for doc in subrange]

        if not subrange_seq_nos:
            break  # No more documents to process

        min_seq_no = subrange_seq_nos[0]
        max_seq_no = subrange_seq_nos[-1]
        ranges.append((min_seq_no, max_seq_no))

        last_max_seq_no = max_seq_no

    return ranges

def get_id_ranges(source_collection, num_ranges, field_name='customerid'):
    """
    Divide the collection into ranges based on a specified field.
    """
    first_doc = source_collection.find_one(sort=[(field_name, 1)])
    last_doc = source_collection.find_one(sort=[(field_name, -1)])

    if not first_doc or not last_doc:
        raise ValueError("Collection is empty or field is missing.")

    first_id = first_doc[field_name]
    last_id = last_doc[field_name]

    # Assuming customerid is a string of digits, convert to integer for range calculation
    first_val = int(first_id)
    last_val = int(last_id)

    val_range = last_val - first_val
    range_size = val_range // num_ranges

    ranges = []
    for i in range(num_ranges):
        start_val = first_val + i * range_size
        end_val = start_val + range_size

        # Convert back to string format if necessary
        start_id = str(start_val)
        end_id = str(end_val)

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
