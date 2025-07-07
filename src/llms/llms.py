import os
import json
import re
import time
import numpy as np
from dotenv import load_dotenv
from google import genai
from src.llms.prompts import _RANKER_PROMPT, _CONTEXT_PROVIDER_PROMPT
from src.query_emb import search_query
from src.utils.logger import logger

load_dotenv()
model_name = os.getenv('MODEL_NAME')

# Formats the input for LLM


def form_query_input(query: str, top_k_results: list[dict]) -> str:
  input: str = f"Query: {query}\nProduct Chunks: \n"
  for i, result in enumerate(top_k_results):
    input += f"\nItem {i + 1}:\n"
    for key, value in result.items():
      input += f"{key}: {value}\n"
  return input

# Inputs the prompt and Input to return a JSON like response
# that handles ranking of items.


def form_response(query: str, model_name: str):
  query = query.lower().strip()
  logger.info(f"Forming response for query: '{query}'")

  client = genai.Client()

  # Adding more context to the query so as to obtain better embeddings
  try:
    logger.info("Generating expanded query from LLM.")
    t_start = time.time()
    expanded_query = client.models.generate_content(
        model=model_name,
        contents=_CONTEXT_PROVIDER_PROMPT + query
    )
    logger.info(
        f"Expanded query generated in {time.time() - t_start:.2f}s. New query: '{expanded_query.text.strip()}'")
    # **BUG FIX**: Use the expanded query for the search
    top_k_results = search_query(expanded_query.text, top_k=10)
  except Exception as e:
    logger.error(
        f"Failed to get expanded query or search results. Falling back to original query. Error: {e}")
    top_k_results = search_query(query, top_k=10)

  input_text = _RANKER_PROMPT + form_query_input(query, top_k_results)

  logger.info("Sending ranked list request to LLM.")
  t_start = time.time()
  response = client.models.generate_content(
      model=model_name,
      contents=input_text,
  )
  logger.info(
      f"LLM ranking response received in {time.time() - t_start:.2f}s.")

  raw_text = response.text
  clean_text = re.sub(r"```(json)?", "", raw_text, flags=re.IGNORECASE).strip()
  try:
    parsed_results = json.loads(clean_text)
  except json.JSONDecodeError:
    logger.warning(f"Response is not Valid JSON. Raw output:\n{raw_text}")
    parsed_results = {}

  final_results = {}

  for obj_key, obj_value in parsed_results.items():
    if not isinstance(obj_value, dict):
      continue

    # Ensure all keys are present before accessing them
    name = obj_value.get("Name", "N/A")
    explanation = obj_value.get("Explanation", "No explanation provided.")
    score = obj_value.get("score")

    if isinstance(explanation, str):
      explanation = explanation.strip()
    if isinstance(name, str):
      name = name.strip()

    if isinstance(score, (int, float, np.integer, np.floating)):
      score = float(score)
    else:
      score = 0.0  # Default score if missing or invalid

    if score < 0 or score > 1:
      continue

    final_results[obj_key] = {
        "Name": name,
        "Explanation": explanation,
        "score": score,
    }

  logger.info(
      f"Successfully parsed {len(final_results)} valid products from LLM response.")
  return json.dumps(final_results, indent=2)


if __name__ == '__main__':
  query = "Bedsheets and mattresses"

  model_name = os.getenv('MODEL_NAME')

  results = form_response(query, model_name)
  if not results:
    print("No valid products in the DB")

  else:
    parsed_results = json.loads(results)
    for obj_key, obj_value in parsed_results.items():
      print(f"--- {obj_key} ---")
      print(f"Name: {obj_value['Name']}")
      print(f"Explanation: {obj_value['Explanation']}")
      print(f"Score: {obj_value['score']}")
