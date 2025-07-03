import os
import uuid
from tqdm import tqdm
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

load_dotenv()

prod_corpus = "../Corpus/prod_corpus.txt"
query_corpus = "../Corpus/query_corpus.txt"

embedding_model_name = os.getenv("EMBEDDING_MODEL_NAME")

def extract_chunks_from_file(filepath):
  with open(filepath, "r", encoding="utf-8") as f:
    text = f.read()

  # Split by  [CLS] and keep only non-empty pieces
  raw_chunks = text.split("[CLS]")
  chunks = []
  for chunk in raw_chunks:
    chunk = chunk.strip()
    if chunk.endswith("[SEP]"):
      chunk = chunk[:-5].strip() # remove "[SEP]"
    if chunk:
      chunks.append(chunk)
  return chunks

embedder = SentenceTransformer(embedding_model_name)
def embed_text(text, embedder):
  embeddings = embedder.encode(text)
  return embeddings.tolist()

# =========================================================================
ca_certs = os.getenv("ELASTICSEARCH_CA_CERTIFICATE")
es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", os.getenv("ELASTICSEARCH_PASSWORD")),
    ca_certs=ca_certs,
)
# =========================================================================

def create_index(es_client, index_name, embedding_dim=384):
  if es_client.indices.exists(index=index_name):
    es_client.indices.delete(index=index_name)
    print("Delete index " + index_name)

  mapping = {
    "mappings": {
      "properties": {
        "text": {"type": "text"},
        "embedding": {"type": "dense_vector", "dims": embedding_dim},
        "type": {"type": "keyword"},
        "uuid": {"type": "keyword"}
      }
    }
  }

  es_client.indices.create(index=index_name, body=mapping)
  print(f"Index '{index_name}' created.")

def index_chunk(es_client, index_name, text, embedding, chunk_type):
  doc = {
    "text": text,
    "embedding": embedding,
    "type": chunk_type,
    "uuid": str(uuid.uuid4())
  }
  es_client.index(index=index_name, body=doc)

def process_and_index(file_path, index_name, chunk_type, embedder, es_client):
  chunks = extract_chunks_from_file(file_path)
  print(f"Extracted {len(chunks)} chunks from {file_path}")

  for chunk in tqdm(chunks, desc=f"Indexing {chunk_type}", unit="chunk"):
    embedding = embed_text(chunk, embedder)
    index_chunk(es_client, index_name, chunk, embedding, chunk_type)

if __name__ == "__main__":
  index_name = "corpus_chunks"
  embedding_dim = 384
  create_index(es, index_name, embedding_dim)

  # Process product corpus
  process_and_index(prod_corpus, index_name, embedding_dim, embedder, es)

  # Process query corpus
  process_and_index(query_corpus, index_name, embedding_dim, embedder, es)

  print("All chunks indexed successfully.")