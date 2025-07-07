import os
import time
import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
from concurrent.futures import ThreadPoolExecutor
from src.utils.logger import logger

load_dotenv()

# --- Elasticsearch Connection ---
ca_certs = os.getenv("ELASTICSEARCH_CA_CERTIFICATE")
es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", os.getenv("ELASTICSEARCH_PASSWORD")),
    ca_certs=ca_certs,
)

# --- Embedding Model ---
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
  Find the most relevant keyword and semantic hits for the query in parallel.
  Args:
    query (str): The query to search for.
    top_k: Gives the top k results for the query.

  Returns:
    A concatenated list of top k results of both searches, yielding a list of
    size 2k.
  """
  start_time = time.time()
  logger.info(f"Starting parallel search for query: '{query[:50]}...'")

  with ThreadPoolExecutor(max_workers=2) as executor:
    future_semantic = executor.submit(
        search_elasticsearch_embedding, query, top_k)
    future_keywords = executor.submit(search_es_keywords, query, top_k)

    semantic_hits = future_semantic.result()
    keyword_hits = future_keywords.result()

  top_hits = semantic_hits + keyword_hits
  total_time = time.time() - start_time
  logger.info(
      f"Parallel search completed. Got {len(top_hits)} total hits in {total_time:.4f} seconds.")

  return top_hits


def search_similar_queries(query: str, top_k: int = 2) -> list[str]:
  """
  Search for similar queries (chunk_type = 'query') in Elasticsearch.

  Args:
    query (str): The query string to find similar queries for:
    top_k (int): Number of similar queries to return

  Returns:
    List of strings with 'query_text'
  """
  logger.info(f"Searching for {top_k} similar queries for: '{query}'")
  start_time = time.time()
  query_embedding = model.encode(query)

  # Search for top_k similar queries
  knn_query = {
      "query": {
          "bool": {
              "filter": [
                  {"term": {"type": "query"}}
              ],
              "must": {
                  "knn": {
                      "field": "embedding",
                      "query_vector": query_embedding.tolist(),
                      "k": top_k,
                      "num_candidates": 20
                  }
              }
          }
      }
  }

  response = es.search(
      index="corpus_chunks",
      body=knn_query,
  )

  results = [hit["_source"]["text"] for hit in response["hits"]["hits"]]
  logger.info(
      f"Found {len(results)} similar queries in {time.time() - start_time:.4f}s.")

  return results


if __name__ == "__main__":
  queries = [
      "sunflowers",
      "bedshits and mattersess",
      "Headphones",
      "wine bar",
      "wall art"
  ]

  # Example of searching for product chunks
  for query in queries:
    hits = search_query(query, top_k=10)
    print(f"\n--- Product Search Results for '{query}' ---")
    # for hit in hits[:2]: # Show first 2 for brevity
    #   print(f"{hit['content']}\nScore: {hit['score']:.4f}\n{'='*20}")

  # Example of searching for similar queries
  for query in queries:
    print(f"\n--- Similar Queries for '{query}' ---")
    results = search_similar_queries(query)
    for result in results:
      print(f"-> {result}")
    print('=' * 65)
