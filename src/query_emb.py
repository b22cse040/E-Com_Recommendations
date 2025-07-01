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
def search_elasticsearch_embedding(query: str, top_k: int = 5) -> list[dict]:
  '''
  Performs kNN search on Elasticsearch using dense embeddings.

  Args:
    query_text (str) : The text query to search for.
    top_k (int) : The number of top results to return.

  Returns:
    List of dictionaries containing the top k results.
  '''
  query_embedding = model.encode(query)
  knn_query = {
    "knn" : {
      "field" : "embedding",
      "query_vector" : query_embedding.tolist(),
      "k" : top_k,
      "num_candidates" : max(10 * top_k, 100),
    }
  }

  response = es.search(
    index="corpus_chunks",
    body=knn_query,
    source=["content"]
  )

  results = []
  for hit in response["hits"]["hits"]:
    results.append({
      "content" : hit["_source"]["content"],
      "score" : hit["_score"],
    })

  return results

def search_es_keywords(query: str, top_k: int = 5) -> list[dict]:
  keyword_query = {
    "query" : {
      "match" : {
        "content" : {
          "query" : query,
          # "operator": "and",
          "fuzziness" : "AUTO",
        }
      }
    },
    "size" : top_k,
  }

  response = es.search(index="corpus_chunks", body=keyword_query)
  results = []

  for hit in response["hits"]["hits"]:
    results.append({
      "content" : hit["_source"]["content"],
      "score" : hit["_score"],
    })

  return results

def search_query(query: str, top_k: int = 5) -> list[dict]:
  semantic_hits = search_elasticsearch_embedding(query, top_k)
  keywords_hits = search_es_keywords(query, top_k)
  top_hits = semantic_hits + keywords_hits
  return top_hits

def form_response(top_hits: list[dict], model: str) -> str:
  pass

if __name__ == "__main__":
  hits = search_query("headpnhoes", top_k=3)
  for hit in hits:
    print(f"{hit['content']}\n{hit["score"]}")