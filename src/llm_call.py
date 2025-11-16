import os, json, re
import numpy as np
from typing import Optional
from dotenv import load_dotenv
from google import genai
from redis import Redis
from sentence_transformers import SentenceTransformer
from src.llms.prompts import _RANKER_PROMPT, _CONTEXT_PROVIDER_PROMPT
from src.query_emb import search_query, load_es
from src.vector_DB import embed_text
from saved_crossencoder.FT_Ranker import *

es = load_es()
# -----------------------------------------------------------------------
## Formats the input for LLM
def form_query_input(query: str, top_k_results: list[dict]) -> str:
  input: str = f"Query: {query}\nProduct Chunks: \n"
  for i, result in enumerate(top_k_results):
    input += f"\nItem {i + 1}:\n"
    for key, value in result.items():
      input += f"{key}: {value}\n"
  return input

def expand_query(query: str, client: genai.client, model_name: str) -> str:
  query = query.lower().strip()
  expanded_query = client.models.generate_content(
    model=model_name,
    contents=_CONTEXT_PROVIDER_PROMPT + query
  )
  return expanded_query.text.strip()

def clean_response(raw_text: str):
  """
  Clean LLM raw text output and convert to structured dict with validated field
  """
  # Remove ```json or``` markers
  clean_text = re.sub(r"```(json)?", "", raw_text, flags=re.IGNORECASE).strip()
  try:
    parsed_results = json.loads(clean_text)
  except json.JSONDecodeError:
    print(f"Warning: Response is not valid JSON. Raw output:\n{raw_text}")
    parsed_results = {}

  final_results = {}

  for obj_key, obj_value in parsed_results.items():
    if not isinstance(obj_value, dict):
      continue

    name = obj_value["Name"]
    explanation = obj_value["Explanation"]
    # score = obj_value["score"]

    if isinstance(explanation, str):
      explanation = explanation.strip()
    if isinstance(name, str):
      name = name.strip()

    # print(f"Type before float conversion: {type(score)}")
    # if isinstance(score, (int, float, np.integer, np.floating)):
    #   score = float(score)
    # print(f"Type before float conversion: {type(score)}")

    # if score < 0 or score > 1:
    #   continue

    final_results[obj_key] = {
      "Name": name,
      "Explanation": explanation,
      # "score": score,
    }

  return json.dumps(final_results, indent=2)
# ------------------------------------------------------------------------
# def compute_vector(text: str, embedder: SentenceTransformer) -> np.ndarray:
  # return embedder.encode([text], normalize_embeddings=True)[0]

def cosine_similarity(vector1: np.ndarray, vector2: np.ndarray) -> float:
  # Note both embeddings are already normalized
  dot_product  = np.dot(vector1, vector2)
  return dot_product

def cache_query(query: str, query_vector: np.ndarray, response, redis_client : Redis, expiry: int=7200) -> None:
  # response id JSON format
  key = f"query_cache:{query.lower().strip()}"
  data = {
    "query" : query,
    "query_vector" : query_vector,
    "llm_response" : response,
  }
  redis_client.setex(key, expiry, json.dumps(data))

def find_cached_similar_query(new_vector: np.ndarray, redis_client: Redis, threshold=0.9):
  for key in redis_client.scan_iter(match="query_cache:*"):
    cached_data = json.loads(redis_client.get(key))
    cached_vector = np.array(cached_data["query_vector"], dtype=np.float32)
    sim = cosine_similarity(new_vector, cached_vector)
    if sim >= threshold:
      print(f"Found similar query: {cached_data['query']} (similarity: {sim:.4f})")
      return cached_data["llm_response"]
  return None
# ---------------------------------------------------------------------------

## Inputs the prompt and Input to return a JSON like response
## that handles ranking of items.
def form_response(
    query: str,
    model_name: str,
    ranker_model, tokenizer,
    embedder, device,
    redis_client: Optional[Redis],
    user_metadata: dict = None,
    ranker_prompt=_RANKER_PROMPT
):
  query = query.lower().strip()
  query_vector = embed_text(query, embedder, device)
  if redis_client is not None:
    cached_response = find_cached_similar_query(query_vector, redis_client=redis_client)
    if cached_response:
      return cached_response

  client = genai.Client()

  ## Adding more context to the query so as to obtain better embeddings
  expanded_query = expand_query(query, client, model_name=model_name)
  print(expanded_query)

  # Finding the top-k results keyword and semantically
  top_k_results = search_query(expanded_query, top_k=10, embedder=embedder, device="cpu")

  top_k_results_ranked = rank_embeddings(query=query, model=ranker_model, tokenizer=tokenizer, device=device, max_len=128, top_hits=top_k_results)
  print(top_k_results_ranked)

  # Inject User Metadata
  if user_metadata is None:
    user_metadata = {}

  age = user_metadata.get("age", "unknown")
  gender = user_metadata.get("gender", "unknown")
  previous_liked = user_metadata.get("previous_liked", [])
  previous_disliked = user_metadata.get("previous_disliked", [])

  metadata_text = f"""
  User Metadata:
  - Age: {age}
  - Gender: {gender}
  - Previously Liked: {previous_liked}
  - Previously Disliked: {previous_disliked}
  """

  # forming input for LLM -> LLM(prompt + input)
  input_text = (
    ranker_prompt
    + '\n'
    + metadata_text
    + '\n'
    + form_query_input(query, top_k_results_ranked)
  )

  # Generating response
  response=client.models.generate_content(
    model=model_name,
    contents=input_text,
  )

  raw_text = response.text

  # Clean the results
  final_results = clean_response(raw_text)

  if redis_client is not None:
    cache_query(query, query_vector, final_results, redis_client, expiry=7200)
  return final_results

if __name__ == '__main__':
  model_file_path = r"../saved_crossencoder"
  model, tokenizer = load_ranker_model(model_file_path)

  # -----------------------------------------------------------------------
  load_dotenv()
  embedder_model_name = os.getenv('EMBEDDING_MODEL_NAME')
  model_name = os.getenv('MODEL_NAME')
  redis_client = Redis(host='localhost', port=6379, decode_responses=True)
  embedder = SentenceTransformer(embedder_model_name)

  query = "headphones"

  results = form_response(query, model_name, ranker_model=model, tokenizer=tokenizer, device="cpu", embedder=embedder, redis_client=redis_client, ranker_prompt=_RANKER_PROMPT)
  if not results:
    print("No valid products in the DB")

  else:
    parsed_results = json.loads(results)
    for obj_key, obj_value in parsed_results.items():
      print(f"--- {obj_key} ---")
      print(f"Name: {obj_value['Name']}")
      print(f"Explanation: {obj_value['Explanation']}")
      # print(f"Score: {obj_value['score']}")
