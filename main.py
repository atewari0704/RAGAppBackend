import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import inngest
import inngest.fast_api
from inngest.experimental import ai
from dotenv import load_dotenv
from google import genai
import uuid
import os
import datetime

#using qdrantStorage as vectorDatabase and we have created custom functions to make life easy
from vector_db import QdrantStorage
from custom_types import RAGChunkAndSrc,RAGUpsertResult,RAGSearchResult,RAGQueryResult,RAGClearResult
from data_loader import load_and_chunk_pdf, embed_texts

load_dotenv()

# Create an Inngest client
inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
    serializer=inngest.PydanticSerializer()
)

@inngest_client.create_function(
    fn_id="RAG: Ingest PDF",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf"),
)
async def rag_ingest_pdf(ctx: inngest.Context):
    def _load(ctx: inngest.Context) -> RAGChunkAndSrc:
        pdf_path = ctx.event.data["pdf_path"]
        source_id = ctx.event.data.get("source_id", pdf_path)
        chunks = load_and_chunk_pdf(pdf_path)
        return RAGChunkAndSrc(chunks=chunks, source_id=source_id)
    
    def _upsert(chunks_and_src: RAGChunkAndSrc) -> RAGUpsertResult:
        chunks = chunks_and_src.chunks
        source_id = chunks_and_src.source_id
        vecs = embed_texts(chunks)
        ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")) for i in range(len(chunks))]
        payloads = [{"source": source_id, "text": chunks[i]} for i in range(len(chunks))]
        QdrantStorage().upsert(ids, vecs, payloads)
        return RAGUpsertResult(ingested=len(chunks))
    
    chunks_and_src = await ctx.step.run("load-and-chunk",lambda:_load(ctx), output_type=RAGChunkAndSrc)
    ingested = await ctx.step.run("embed-and-upsert",lambda:_upsert(chunks_and_src), output_type=RAGUpsertResult)

    return ingested.model_dump() #converts pydantic object to dict so that it can be serialized and sent as response


@inngest_client.create_function(
    fn_id="RAG: Query PDF",
    trigger=inngest.TriggerEvent(event="rag/query"),
)
async def rag_query(ctx: inngest.Context):
    def _search(question,top_k) -> RAGSearchResult:
        query_vec = embed_texts([question])[0]
        store = QdrantStorage()
        found = store.search(query_vec,top_k) # based on the query it returns relevants chunks(vectors) from the pdf intially uploaded
        return RAGSearchResult(contexts=found["contexts"], sources=found["sources"])

    def _answer_with_gemini(question: str, found: RAGSearchResult) -> RAGQueryResult:
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key: raise ValueError("GEMINI_API_KEY is not set")

        client = genai.Client(api_key=api_key)
        chat = client.chats.create(model="gemini-2.5-flash-lite") #Free-tier

        context_block = "\n\n".join(f"- {c}" for c in found.contexts)
        user_content = (
            "Use the following context to answer the question.\n\n"
            f"Context:\n{context_block}\n\n"
            f"Question: {question}\n"
            "Answer concisely using the context above."
        )

        response = chat.send_message(user_content)
        answer = (response.text or "").strip()

        return RAGQueryResult(
            answer=answer,
            sources=found.sources,
            num_contexts=len(found.contexts),
        )
    

    question = ctx.event.data["question"]
    top_k = ctx.event.data.get("top_k", 5)


    found = await ctx.step.run(
        "search",
        lambda:_search(question, top_k),
        output_type=RAGSearchResult)
    
    result = await ctx.step.run(
        "answer-with-gemini",
        lambda: _answer_with_gemini(question, found),
        output_type=RAGQueryResult,
    )
    
    return result.model_dump()


@inngest_client.create_function(
    fn_id="RAG: Clear All Context",
    trigger=inngest.TriggerEvent(event="rag/clear_all_context"),
)
async def rag_clear_all_context(ctx: inngest.Context):
    def _clear_all_context() -> RAGClearResult:
        message = QdrantStorage().clear_all_collections()
        return RAGClearResult(message = message)

    result = await ctx.step.run("clear-all-context", lambda:_clear_all_context(), output_type=RAGClearResult)
    return result.model_dump()



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


UPLOAD_DIR = "uploads"


@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must have a .pdf extension")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "pdf_path": file_path,
        "source_id": file.filename,
    }


# Serve the Inngest endpoint
inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf, rag_query, rag_clear_all_context])



# you can run the application by doing: uvicorn main:app
# you can then run inngest cli via: npx -y inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest