from app.db.qdrant import qdrant_client


try:
    print("Testing Qdrant connection...")

    collections = qdrant_client.get_collections()

    print("Connected to Qdrant!")
    print(collections)

except Exception as e:
    print("Qdrant connection failed:")
    print(repr(e))