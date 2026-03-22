# from openai import OpenAI
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
from dotenv import load_dotenv

from sentence_transformers import SentenceTransformer

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
EMBED_DIM = 384


load_dotenv()

# instead 
# client = OpenAI()
# EMBED_MODEL = "text-embedding-3-large"
# EMBED_DIM = 3072

splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=200)

def load_and_chunk_pdf(path: str):
    docs = PDFReader().load_data(file=path)
    texts = [d.text for d in docs if getattr(d, "text", None)]
    chunks = []
    for t in texts:
        chunks.extend(splitter.split_text(t))
    return chunks


def embed_texts(texts: list[str]) -> list[list[float]]:
    vectors = model.encode(texts, normalize_embeddings=True)
    return vectors.tolist()

    ## Below is the way to embed text using OpenAI embedding model
    # response = client.embeddings.create(
    #     model=EMBED_MODEL,
    #     input=texts,
    # )
    # return [item.embedding for item in response.data]