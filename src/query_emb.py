import os, time
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

ca_certs = os.getenv("ELASTICSEARCH_CA_CERTIFICATE")
es = Elasticsearch(
  "https://localhost:9200",
  basic_auth=("elastic", os.getenv("ELASTICSEARCH_PASSWORD")),
  ca_certs=ca_certs,
)

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
model = SentenceTransformer(EMBEDDING_MODEL_NAME)

def search_elasticsearch_embedding(query: str, top_k: int = 5) -> list[dict]:
  """
  Searching elasticsearch for embedding
  Args:
    query (str): The query to search for
    top_k (int): the number of top results to return

  Returns:
    Most likely list of embeddings
  """
  query_embedding = model.encode(query)
  knn_query = {
    "knn": {
      "field": "embedding",
      "query_vector": query_embedding.tolist(),
      "k": top_k,
      "num_candidates": max(10 * top_k, 100),
    },
    "_source": ["text"]
  }

  response = es.search(index="corpus_chunks", body=knn_query)

  results = []
  for hit in response["hits"]["hits"]:
    results.append({
      "content": hit["_source"]["text"],
      "score": hit["_score"],
    })

  return results

def search_es_keywords(query: str, top_k: int = 5) -> list[dict]:
  """
  Searching Elasticsearch with keywords
  Args:
    query (str): query to search for:
    top_k (int): number of results to return:

  Returns:
    Most likely results for keyword search.
  """
  keyword_query = {
    "query": {
      "match": {
        "text": {
          "query": query,
          "fuzziness": "AUTO",
        }
      }
    },
    "size": top_k
  }

  response = es.search(index="corpus_chunks", body=keyword_query)

  results = []
  for hit in response["hits"]["hits"]:
    results.append({
      "content": hit["_source"]["text"],
      "score": hit["_score"],
    })

  return results

def search_query(query: str, top_k: int = 5) -> list[dict]:
  """
  Find the most relevant keyword and semantic hits for thw query in parallel.
  Args:
    query (str): The query to search for.
    top_k: Gives the top k results for the query.

  Returns:
    A concatenated list of top k results of both searches, yielding a lisk of
    size 2k.
  """
  start_time = time.time()
  # semantic_hits = search_elasticsearch_embedding(query, top_k)
  # keywords_hits = search_es_keywords(query, top_k)
  # top_hits = semantic_hits + keywords_hits

  with ThreadPoolExecutor(max_workers=2) as executor:
    future_semantic = executor.submit(search_elasticsearch_embedding, query, top_k)
    future_keywords = executor.submit(search_es_keywords, query, top_k)

    semantic_hits = future_semantic.result()
    keyword_hits = future_keywords.result()

  top_hits = semantic_hits + keyword_hits
  total_time = time.time() - start_time
  file_path = "../evals/search_query.txt"

  with open(file_path, "a") as f:
    f.write(f"Got {len(top_hits)} hits in {total_time:.4f} seconds for the query: {query} [PARALLEL]\n")
  return top_hits

def search_similar_queries(query: str, top_k: int = 2) -> list[dict]:
  """
  Search for similar queries (chunk_type = 'query') in Elasticsearch.

  Args:
    query (str): The query string to find similar queries for:
    top_k (int): Number of similar queries to return

  Returns:
    List of dicts with 'query_text' and 'score'
  """
  query_embedding = model.encode(query)

  # Search for top_k similar queries
  knn_query = {
    "knn" : {
      "field": "embedding",
      "query_vector": query_embedding.tolist(),
      "k": top_k,
      "num_candidates": top_k,
    },
    "filter" : {
      "term" : {"type" : "query"}
    }
  }

  response = es.search(
    index="corpus_chunks",
    body=knn_query,
  )

  results = []
  for hit in response["hits"]["hits"]:
    results.append({
      "content": hit["_source"]["text"],
      "score": hit["_score"],
    })

  return results

if __name__ == "__main__":
  queries = ["sunflowers", "bedshits and mattersess", "Headphones", "wine bar", "wall art"]

  for query in queries:
    hits = search_query(query, top_k=10)
    # for hit in hits:
    #   print(f"{hit['content']}\nScore: {hit['score']:.4f}\n{'='*50}")

  ## Average time for parallel: 0.0589 sec, check evals directory
  ## Average time for sequentially: 0.1068 sec, check evals directory
  ## Optimization: 44.85% optimization in time
