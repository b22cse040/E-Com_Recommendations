import os
from dotenv import load_dotenv
from google import genai
from sentence_transformers import SentenceTransformer
from src.llms.prompts import _RANKER_PROMPT
from src.query_emb import search_query

load_dotenv()
embedding_model_name = os.getenv('EMBEDDING_MODEL')
model_name = os.getenv('MODEL_NAME')

def form_query_input(query: str, top_k_results: list[dict]) -> dict:
  pass

def form_response(embedding_model_name: str, query: str, model_name: str):
  query = query.lower().strip()
  model = SentenceTransformer(embedding_model_name)
  model.encode(query)

  client = genai.Client()
  top_k_results = search_query(query, top_k=10)
  top_k = ""
  for result in top_k_results:
    content = result["content"]
    score = result["score"]
    top_k += f"Score: {score}\nContent: {content}\n\n"

  response=client.models.generate_content(
    model=model_name,
    contents=_RANKER_PROMPT + top_k
  )

  return response