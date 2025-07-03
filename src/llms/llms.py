import os, json, re
from dotenv import load_dotenv
from google import genai
from llms.prompts import _RANKER_PROMPT
from query_emb import search_query

load_dotenv()
model_name = os.getenv('MODEL_NAME')

## Formats the input for LLM
def form_query_input(query: str, top_k_results: list[dict]) -> str:
  input: str = f"Query: {query}\nProduct Chunks: \n"
  for i, result in enumerate(top_k_results):
    input += f"\nItem {i + 1}:\n"
    for key, value in result.items():
      input += f"{key}: {value}\n"
  return input

## Inputs the prompt and Input to return a JSON like response
## that handles ranking of items.
def form_response(query: str, model_name: str):
  query = query.lower().strip()

  client = genai.Client()
  top_k_results = search_query(query, top_k=10)
  input_text = _RANKER_PROMPT + form_query_input(query, top_k_results)

  response=client.models.generate_content(
    model=model_name,
    contents=input_text,
  )

  raw_text = response.text
  clean_text = re.sub(r"```(json)?", "", raw_text, flags=re.IGNORECASE).strip()
  try:
    parsed_results = json.loads(clean_text)
  except json.JSONDecodeError:
    print(f"Warning: Response is not Valid JSON. Raw output:\n{raw_text}")
    parsed_results = {}

  final_results = {}

  for obj_key, obj_value in parsed_results.items():
    if not isinstance(obj_value, dict):
      continue

    name = obj_value["Name"]
    explanation = obj_value["Explanation"]
    score = obj_value["score"]

    if not isinstance(explanation, str):
      continue
    if not isinstance(score, float):
      continue
    if not isinstance(name, str):
      continue

    if score < 0 or score > 1:
      continue

    final_results[obj_key] = {
      "Name": name,
      "Explanation": explanation,
      "score": score,
    }

  return json.dumps(final_results, indent=2)

# if __name__ == '__main__':
#   query = "Bedsheets and mattresses"
#
#   model_name = os.getenv('MODEL_NAME')
#
#   results = form_response(query, model_name)
#   if not results:
#     print("No valid products in the DB")
#
#   else:
#     for obj_key, obj_value in results.items():
#       print(f"--- {obj_key} ---")
#       print(f"Name: {obj_value['Name']}")
#       print(f"Explanation: {obj_value['Explanation']}")
#       print(f"Score: {obj_value['Score']}")
#       print()