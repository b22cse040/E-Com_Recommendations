from transformers import AutoTokenizer, AutoModel
import torch.nn as nn
import torch.nn.functional as F
import torch, os, json

## Building the CrossEncoder for inference
class CrossEncoder(nn.Module):
  def __init__(self, encoder):
    super().__init__()
    self.encoder = encoder
    hidden_size = encoder.config.hidden_size
    self.reg_head = nn.Linear(hidden_size, 1)  # regression
    self.cls_head = nn.Linear(hidden_size, 4)  # classification (4 classes)

  def forward(self, input_ids, attention_mask):
    outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
    pooled_output = outputs.last_hidden_state[:, 0, :]  # CLS token
    reg_logits = self.reg_head(pooled_output).squeeze(-1)
    cls_logits = self.cls_head(pooled_output)
    return reg_logits, cls_logits

## Fn to load the fine-tuned model
def load_ranker_model(model_path: str, device: str = "cpu"):
  """
  Load a fine-tuned CrossEncoder model + tokenizer from disk.

  Args:
    model_path (str): Path to the saved model directory
    device (str): 'cpu' or 'cuda'

  Returns:
    model (CrossEncoder): Loaded pyTorch model in eval mode
    tokenizer (Tokenizer): HF_Tokenizer
  """
  ## Load encoder back-bone
  encoder = AutoModel.from_pretrained(model_path, local_files_only=True)

  ## Load Tokenizer
  tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)

  ## Build CE with custom heads
  model = CrossEncoder(encoder)

  ## FT wts
  state_dict = torch.load(
    os.path.join(model_path, "pytorch_model.bin"),
    map_location=device
  )

  ## Put in eval mode for inference
  model.load_state_dict(state_dict)
  model.to(device)
  model.eval()
  return model, tokenizer

def rank_embeddings(query: str, model: CrossEncoder, tokenizer, top_hits: list[dict], device="cpu", max_len=128):
  '''
  Function to rank the embeddings using CrossEncoder model. top_hits comes from
  search_query fn that returns the top-k/2 semantically and top-k/2 by keywords.
  The purpose of this fn is to rank those embeddings using CrossEncoder model. The
  output will is a ranked list of embeddings that will be given to the LLM, for personalization.
  '''
  products = [hit["content"] for hit in top_hits]

  encoded = tokenizer(
    [query] * len(products),
    products,
    padding="max_length",
    return_tensors="pt",
    max_length=max_len,
    truncation=True,
  ).to(device)

  model.eval()
  with torch.no_grad():
    reg_logits, cls_logits = model(encoded["input_ids"], encoded["attention_mask"])
    reg_scores = torch.nn.functional.softplus(
      reg_logits).cpu().numpy().flatten()
    cls_preds = torch.argmax(
      torch.nn.functional.softmax(cls_logits, dim=-1), dim=-1
    ).cpu().numpy()

    reg_scores = F.softplus(reg_logits)
    reg_scores = F.normalize(reg_scores, p=2, dim=-1)  # L2 normalize
    reg_scores = reg_scores.cpu().numpy().flatten()

  ranked_hits = []
  for hit, r_score, cls in zip(top_hits, reg_scores, cls_preds):
    ranked_hits.append({
      "content": hit["content"],
      "cross_score": float(cls),
    })

  ranked_hits.sort(key=lambda x: x["cross_score"], reverse=True)
  return [{"content" : hit["content"]} for hit in ranked_hits]