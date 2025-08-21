from __future__ import annotations
from functools import lru_cache
from transformers import AutoTokenizer, AutoModel


@lru_cache(maxsize=1)
def load_model_and_tokenizer(model_name: str):
    model = AutoModel.from_pretrained(model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model.eval()
    return model, tokenizer