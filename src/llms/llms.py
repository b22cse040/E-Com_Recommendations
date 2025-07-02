import os
from dotenv import load_dotenv
from google import genai
from sentence_transformers import SentenceTransformer
from src.llms.prompts import _RANKER_PROMPT
from src.query_emb import search_query

load_dotenv()
embedding_model_name = os.getenv('EMBEDDING_MODEL')
model_name = os.getenv('MODEL_NAME')

def form_query_input(query: str, top_k_results: list[dict]) -> str:
  input: str = query + "\n"
  for i, result in enumerate(top_k_results):
    input += f"\nItem {i + 1}:\n"
    for key, value in result.items():
      input += f"{key}: {value}\n"
  return input

def form_response(embedding_model_name: str, query: str, model_name: str):
  query = query.lower().strip()
  model = SentenceTransformer(embedding_model_name)
  model.encode(query)

  client = genai.Client()
  top_k_results = search_query(query, top_k=10)

  response=client.models.generate_content(
    model=model_name,
    contents=_RANKER_PROMPT + form_query_input(query, top_k_results),
  )

  return response