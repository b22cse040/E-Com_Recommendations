import os, time, torch
import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
from concurrent.futures import ThreadPoolExecutor
from saved_crossencoder.FT_Ranker import CrossEncoder, load_ranker_model
from src.vector_DB import embed_text

load_dotenv()
def load_es():
  ca_certs = os.getenv("ELASTICSEARCH_CA_CERTIFICATE")
  es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", os.getenv("ELASTICSEARCH_PASSWORD")),
    ca_certs=ca_certs,
  )

  return es

def search_elasticsearch_embedding(query: str, model, model_tokenizer, device: str, top_k: int = 5) -> list[dict]:
  """
  Searching elasticsearch for embedding
  Args:
    query (str): The query to search for
    top_k (int): the number of top results to return

  Returns:
    Most likely list of embeddings
  """
  query_embedding = embed_text(query, model, model_tokenizer, device)
  # knn_query = {
  #   "knn": {
  #     "field": "embedding",
  #     "query_vector": query_embedding, #.tolist(),
  #     "k": top_k,
  #     "num_candidates": max(10 * top_k, 100),
  #     # "chunk_type" : "product"
  #   },
  #   "_source": ["text"]
  # }
  if isinstance(query_embedding, torch.Tensor):
    query_embedding = query_embedding.detach().cpu().numpy().tolist()
  knn_query = {
    "query": {
      "bool": {
        "filter": [{"term": {"chunk_type": "product"}}]
      }
    },
    "knn": {
      "field": "embedding",
      "query_vector": query_embedding,
      "k": top_k,
      "num_candidates": max(10 * top_k, 100)
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

## Average time for parallel: 0.0589 sec, check evals directory
## Average time for sequentially: 0.1068 sec, check evals directory
## Optimization: 44.85% optimization in time
def search_query(query: str, model, model_tokenizer, device, top_k: int = 5) -> list[dict]:
  """
  Find the most relevant keyword and semantic hits for thw query in parallel.
  Args:
    query (str): The query to search for.
    model_tokenizer (CrossEncoder): CrossEncoder model for tokenizing
    top_k: Gives the top k results for the query.

  Returns:
    A concatenated list of top k results of both searches, yielding a list of
    size 2k.
  """
  # start_time = time.time()
  # semantic_hits = search_elasticsearch_embedding(query, top_k)
  # keywords_hits = search_es_keywords(query, top_k)
  # top_hits = semantic_hits + keywords_hits

  with ThreadPoolExecutor(max_workers=2) as executor:
    start_time = time.time()
    future_semantic = executor.submit(search_elasticsearch_embedding, query, model, model_tokenizer, device, top_k)
    future_keywords = executor.submit(search_es_keywords, query, top_k)

    semantic_hits = future_semantic.result()
    keyword_hits = future_keywords.result()

  top_hits = semantic_hits + keyword_hits
  total_time = time.time() - start_time
  print(f"Executed in {total_time} seconds")
  # file_path = "../evals/search_query.txt"
  #
  # with open(file_path, "a") as f:
  #   f.write(f"Got {len(top_hits)} hits in {total_time:.4f} seconds for the query: {query} [PARALLEL]\n")
  return top_hits

# def search_similar_queries(query: str, model, model_tokenizer, device: str, top_k: int = 2) -> list[str]:
#   """
#   Search for similar queries (chunk_type = 'query') in Elasticsearch.
#
#   Args:
#     query (str): The query string to find similar queries for:
#     top_k (int): Number of similar queries to return
#
#   Returns:
#     List of string with 'query_text'
#   """
#   query_embedding = embed_text(query, model, model_tokenizer, device)
#
#   # Search for top_k similar queries
#   knn_query = {
#     "query": {
#       "bool": {
#         "filter": [
#           {"term": {"type": "query"}}
#         ],
#         "must": {
#           "knn": {
#             "field": "embedding",
#             "query_vector": query_embedding,
#             "k": top_k,
#             "num_candidates": 20
#           }
#         }
#       }
#     }
#   }
#
#   response = es.search(
#     index="corpus_chunks",
#     body=knn_query,
#   )
#
#   results = []
#   for hit in response["hits"]["hits"]:
#     # results.append({
#     #   "content": hit["_source"]["text"],
#     #   "score": hit["_score"],
#     # })
#     text = hit["_source"]["text"]
#     score = hit["_score"]
#     # print(type(score))
#
#     if isinstance(score, (np.integer, np.floating)):
#       score = float(score)
#
#     # print(type(score))
#
#     results.append(text)
#
#   return results

if __name__ == "__main__":

  load_dotenv()

  # EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
  # model = SentenceTransformer(EMBEDDING_MODEL_NAME)
  model_file_path = "../saved_crossencoder"
  model, tokenizer = load_ranker_model(model_file_path, device="cpu")


  queries = [
    "outside screen for patio"
  ]
  #
  for query in queries:
    hits = search_query(query, top_k=10, model_tokenizer=tokenizer, model=model, device="cpu")
    for hit in hits:
      print(f"{hit['content']}\nScore: {hit['score']:.4f}\n{'='*50}")
  # for query in queries:
  #   print(query, ": \n")
  #   results = search_similar_queries(query, tokenizer)
  #   for result in results:
  #     print(f"{result}\n")
  #   print('=' * 65)