from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

# if the transformer model changes then changes the DIM below

class QdrantStorage:
    def __init__(self, url="http://localhost:6333", collection="docs", dim=768):
        self.client = QdrantClient(url=url, timeout=30)
        self.collection = collection
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

    # to update or insert you must have PoinStructs which consist of id, vector and the payload
    def upsert(self, ids, vectors, payloads):
        points = [PointStruct(id=ids[i], vector=vectors[i], payload=payloads[i]) for i in range(len(ids))]
        self.client.upsert(collection_name=self.collection, points=points)


    def search(self, query_vector, top_k=5):
        response = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        )
        results = response.points or []

        contexts = []
        sources = set()

        for r in results:
            payload = r.payload or {}
            text = payload.get("text", "")
            source = payload.get("source", "")
            if text:
                contexts.append(text)
                if source:
                    sources.add(source)

        return {"contexts": contexts, "sources": sorted(sources)}