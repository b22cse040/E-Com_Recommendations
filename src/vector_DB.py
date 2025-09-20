import os
import uuid
import torch
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

load_dotenv()
embedding_model_name = os.getenv("EMBEDDING_MODEL_NAME")
embedder = SentenceTransformer(embedding_model_name)
print(embedding_model_name)
# ======================================================
# Embedding Model
# ======================================================
def embed_text(text, embedder, device):
  with torch.no_grad():
    vec = embedder.encode(text, convert_to_tensor=True, device=device, normalize_embeddings=True)
    return vec.cpu().tolist()

# ======================================================
# ES Helpers
# ======================================================
def create_index(es_client, index_name, embedding_dim=768):
  if es_client.indices.exists(index=index_name):
    es_client.indices.delete(index=index_name)
    print("Deleted index " + index_name)

  mapping = {
    "mappings": {
      "properties": {
        "text": {"type": "text"},
        "embedding": {"type": "dense_vector", "dims": embedding_dim},
        "type": {"type": "keyword"},  # query / product
        "uuid": {"type": "keyword"},
        # "esci_label": {"type": "keyword"},
        "source": {"type": "keyword"}  # train/test
      }
    }
  }

  es_client.indices.create(index=index_name, body=mapping)
  print(f"Index '{index_name}' created.")

def index_entry(es_client, index_name, text, embedding, chunk_type, source):
  doc = {
    "text": text,
    "embedding": embedding,
    "chunk_type": chunk_type,
    "uuid": str(uuid.uuid4()),
    "source": source,
  }

  es_client.index(index=index_name, body=doc)

def process_and_index_dataset(
    file_path, index_name, embedder, es_client,
    device, source, seen_products, # seen_queries,
):
  df = pd.read_csv(file_path)
  print(f"Loaded {len(df)} rows from {file_path}.")

  for _, row in tqdm(df.iterrows(), total=len(df), desc=f"Indexing {source}", unit="row"):
    # query_text = str(row["query"]).strip()
    product_text = str(row["product_input"]).strip()

    # ## --- Handle Queries ---
    # if query_text and query_text not in seen_queries:
    #   query_embedding = embed_text(query_text, model, tokenizer, device)
    #   index_entry(es_client, index_name, query_text, query_embedding, chunk_type="query", source=source)
    #   seen_queries.add(query_text)
    # else: continue

    ## --- Handle Product information ---
    if product_text and product_text not in seen_products:
      product_embedding = embed_text(product_text, embedder, device)
      index_entry(es_client, index_name, product_text, product_embedding, chunk_type="product", source=source)
      seen_products.add(product_text)
    else: continue

  return

# ======================================================
# MAIN
# ======================================================
if __name__ == "__main__":

  train_file = "../Corpus/filtered_train.csv"
  test_file = "../Corpus/filtered_test.csv"

  device = "cuda" if torch.cuda.is_available() else "cpu"

  embedding_model_name = os.getenv("EMBEDDING_MODEL_NAME")
  embedder = SentenceTransformer(embedding_model_name)
  ca_certs = os.getenv("ELASTICSEARCH_CA_CERTIFICATE")
  es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", os.getenv("ELASTICSEARCH_PASSWORD")),
    ca_certs=ca_certs,
  )

  index_name = "corpus_chunks"
  create_index(es, index_name, embedding_dim=384)

  seen_queries, seen_products = set(), set()

  # process_and_index_dataset(
  #   file_path=train_file,
  #   index_name=index_name,
  #   model=model,
  #   tokenizer=tokenizer,
  #   es_client=es,
  #   device=device,
  #   source="train",
  #   seen_queries=seen_queries,
  #   seen_products=seen_products
  # )

  process_and_index_dataset(
    file_path=test_file,
    index_name=index_name,
    embedder=embedder,
    es_client=es,
    device=device,
    source="test",
    seen_products=seen_products
  )