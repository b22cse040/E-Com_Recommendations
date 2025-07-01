import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch

load_dotenv()

# ========================================================================
ca_certs = os.getenv("ELASTICSEARCH_CA_CERTIFICATE")
es = Elasticsearch(
  "https://localhost:9200",
  basic_auth=("elastic", os.getenv("ELASTICSEARCH_PASSWORD")),
  ca_certs=ca_certs,
)

# ========================================================================
MODEL_NAME = "all-MiniLM-L6-v2"

model = SentenceTransformer(MODEL_NAME)
query_text = "headphones"
query_embedding = model.encode(query_text, normalize=True)

knn_query = {
  "knn" : {
    "field" : "embedding",
    "query_vector" : query_embedding.tolist(),
    "k" : 10,
    "num_candidates" : 100
  }
}

response = es.search(index="corpus_chunks", body={"query": knn_query}, source=["content"])

for hit in response['hits']['hits']:
  print(hit["_source"]["content"], "| Score: ", hit["_score"])