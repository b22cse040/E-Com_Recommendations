from transformers import AutoTokenizer, AutoModel
import torch.nn as nn
import torch, os

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