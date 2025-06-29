import os
import logging
import uuid
import faiss
import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)

filepath = r"D:\Sparkathon\Corpus\corpus.txt"  # corrected path
with open(filepath, "r", encoding="utf-8") as f:
    raw_text = f.read()

splitter = RecursiveCharacterTextSplitter(
    separators=["\n\n", "\n", " "],
    chunk_size=300,
    chunk_overlap=75
)
chunks = splitter.split_text(raw_text)
logging.info(f"Chunking complete. Total chunks created: {len(chunks)}")

embedder = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = embedder.encode(chunks, show_progress_bar=True)
embeddings = np.array(embeddings).astype("float32")

# Create FAISS index
dimension = embeddings.shape[1]  # Should be 384
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)
logging.info("FAISS index created and vectors added.")

id_to_text = {i: chunks[i] for i in range(len(chunks))}

faiss.write_index(index, "faiss_index.index")
with open("id_to_text_mapping.txt", "w", encoding="utf-8") as f:
  for i, text in id_to_text.items():
    f.write(f"{i}\t{text.replace('\n', ' ')}\n")

logging.info("Index and mapping saved.")