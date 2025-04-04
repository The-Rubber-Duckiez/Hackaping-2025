from couchbase.cluster import Cluster, ClusterOptions
from couchbase.auth import PasswordAuthenticator

# Connect to Couchbase
cluster = Cluster("couchbase://127.0.0.1", ClusterOptions(PasswordAuthenticator("user", "password")))
bucket = cluster.bucket("main")
collection = bucket.default_collection()

# Query all message documents
query = "SELECT META().id FROM `main` WHERE `role` = 'assistant'"
result = cluster.query(query)

for row in result:
    doc_id = row["id"]
    doc = collection.get(doc_id).content_as[dict]

    # Check and update the metadata and feedback fields
    if "metadata" not in doc:
        doc["metadata"] = {}
    if "feedback" not in doc["metadata"]:
        doc["metadata"]["feedback"] = {"upvote": 0, "downvote": 0, "answered": 0}

    # Save the updated document
    collection.upsert(doc_id, doc)

print("Schema update completed.")