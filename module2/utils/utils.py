import torch

from module2.classes.Filing import Filing


def embed_filing(filing: Filing, model, tokenizer):
    # Chunks we want to embed
    chunks = filing.text_chunks

    model.eval()

    # Tokenize sentences
    encoded_input = tokenizer(chunks, padding=True, truncation=True, return_tensors='pt')
    # for s2p(short query to long passage) retrieval task, add an instruction to query (not add instruction for passages)
    # encoded_input = tokenizer([instruction + q for q in queries], padding=True, truncation=True, return_tensors='pt')

    # Compute token embeddings
    with torch.no_grad():
        model_output = model(**encoded_input)
        # Perform pooling. In this case, cls pooling.
        chunk_embeddings = model_output[0][:, 0]
    # normalize embeddings
    chunk_embeddings = torch.nn.functional.normalize(chunk_embeddings, p=2, dim=1)
    print("Chunk embeddings:", chunk_embeddings.shape)
    return chunk_embeddings

