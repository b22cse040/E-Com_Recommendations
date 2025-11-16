import os, json
import time
from redis import Redis
from typing import Optional
from dotenv import load_dotenv
from src.llm_call import form_response
# from src.query_emb import search_similar_queries

load_dotenv()
vit_ai_key = os.getenv("VIT_AI_KEY")


# def process_main_query(query: str, model_name: str, ranker_model, tokenizer, embedder, device, redis_client: Optional[Redis]):
#   logs = []
#   start_time = time.time()
#   raw_json_str = form_response(query, model_name, ranker_model=ranker_model, tokenizer=tokenizer, device=device, embedder=embedder, redis_client=redis_client)
#   results = json.loads(raw_json_str)
#   logs.append(f"Main query response time: {time.time() - start_time:.4f} sec")
#   return results, logs

def process_main_query(
    query: str,
    model_name: str,
    ranker_model,
    tokenizer,
    embedder,
    device,
    redis_client: Optional[Redis],
    user_metadata: dict = None
):
    logs = []
    start_time = time.time()

    raw_json_str = form_response(
      query,
      model_name,
      ranker_model=ranker_model,
      tokenizer=tokenizer,
      embedder=embedder,
      device=device,
      redis_client=redis_client,
      user_metadata=user_metadata  # <-- IMPORTANT
    )

    results = json.loads(raw_json_str)
    logs.append(f"Main query response time: {time.time() - start_time:.4f} sec")

    return results, logs


# def fetch_similar_queries(query, model_name):
#   logs = []
#   start_time = time.time()
#   similar_queries = search_similar_queries(query, top_k=2)
#   logs.append(f"Similar queries response time: {time.time() - start_time:.4f} sec")
#   similar_response = {}
#   for sim_query in similar_queries:
#     t0 = time.time()
#     sim_raw_json_str = form_response(sim_query, model_name)
#     sim_results = json.loads(sim_raw_json_str)
#     similar_response[sim_query] = sim_results
#     logs.append(f"Similar query ({sim_query}) response time: {time.time() - t0:.4f} sec")
#
#   logs.append(f"Total similar queries time: {time.time() - start_time:.4f} sec")
#   return similar_queries, similar_response, logs

def save_logs(query, logs, filepath=r"../evals/frontend_time.txt"):
  with open(filepath, "a") as f:
    f.write(f"Query: {query}\n")
    for log in logs:
      f.write(log + '\n')
    f.write("---\n")