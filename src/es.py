# import os
# import faiss
# import numpy as np
# from dotenv import load_dotenv
# from elasticsearch import Elasticsearch
# from tqdm import tqdm
#
# load_dotenv()
#
# # =====================================================================
# index = faiss.read_index("faiss_index.index")
# ntotal = index.ntotal
#
# chunks = []
# with open("id_to_text_mapping.txt", "r", encoding="utf-8") as f:
#   for line in f:
#     parts = line.strip().split("\t", 1)
#     if len(parts) == 2:
#       chunks.append(parts[1])
#
# assert len(chunks) == ntotal, "Mismatch between chunks and vectors"
#
# # =====================================================================
# ca_certs = os.getenv("ELASTICSEARCH_CA_CERTIFICATE")
# es = Elasticsearch(
#   "https://localhost:9200",
#   basic_auth=("elastic", os.getenv("ELASTICSEARCH_PASSWORD")),
#   ca_certs=ca_certs,
# )
# print(es.info())
#
# def create_and_index_chunks():
#   if es.indices.exists(index="corpus_chunks"):
#     es.indices.delete(index="corpus_chunks")
#     print("Deleted old index")
#
#   index_config = {
#     "mappings": {
#       "properties": {
#         "chunk_id": {"type": "integer"},
#         "content": {"type": "text"},
#         "embedding": {
#           "type": "dense_vector",
#           "dims": 384,  # all-MiniLM-L6-v2 dimension size
#           "index": True,
#           "similarity": "cosine"
#         }
#       }
#     }
#   }
#   es.indices.create(index="corpus_chunks", body=index_config)
#   print("Created new index")
#
#   # Index chunks in batches
#   BATCH_SIZE = 200
#   batch_docs = []
#   for i in tqdm(range(ntotal), desc="Indexing chunks"):
#     vec = index.reconstruct(i).astype("float32").tolist()
#     chunk_text = chunks[i]
#
#     doc = {
#       "chunk_id": i,
#       "content": chunk_text,
#       "embedding": vec
#     }
#
#     # Important: set unique _id to avoid duplicates
#     batch_docs.append({"index": {"_index": "corpus_chunks", "_id": i}})
#     batch_docs.append(doc)
#
#     if len(batch_docs) == BATCH_SIZE * 2:
#       es.bulk(body=batch_docs)
#       batch_docs = []
#
#   if batch_docs:
#     es.bulk(body=batch_docs)
#
#   print("All chunks indexed to ES")
#
# if __name__ == "__main__":
#   create_and_index_chunks()