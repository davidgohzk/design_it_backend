from fastapi import FastAPI
from sentence_transformers import SentenceTransformer
import numpy as np
import requests

app = FastAPI()

# Load embedding model
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# Load documents
with open("data/docs.txt", "r") as f:
    documents = [line.strip() for line in f if line.strip()]

doc_embeddings = embed_model.encode(documents)

def retrieve(query, k=3):
    query_embedding = embed_model.encode([query])[0]
    similarities = np.dot(doc_embeddings, query_embedding)
    top_k_idx = np.argsort(similarities)[-k:]
    return [documents[i] for i in top_k_idx]

def build_prompt(query, context_chunks):
    context = "\n".join(context_chunks)
    return f"""
You must answer ONLY using the provided context.
If the answer is not in the context, say "I don't know".

Context:
{context}

Question:
{query}

Answer:
"""

def call_llm(prompt):
    res = requests.post("http://localhost:11434/api/generate", json={
        "model": "tinyllama",
        "prompt": prompt,
        "stream": False
    })
    return res.json()["response"]

@app.get("/")
def root():
    return {"status": "running"}

@app.post("/ask")
async def ask(question: str):
    context = retrieve(question)
    prompt = build_prompt(question, context)
    answer = call_llm(prompt)
    return {"answer": answer, "context_used": context}