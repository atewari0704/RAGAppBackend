import logging
from fastapi import FastAPI
import uvicorn
import inngest
import inngest.fast_api
from inngest.experimental import ai
from dotenv import load_dotenv
import uuid
import os
import datetime

#using qdrantStorage as vectorDatabase and we have created custom functions to make life easy
from vector_db import QdrantStorage
from custom_types import RAGChunkAndSrc,RAGUpsertResult,RAGSearchResult,RAGQueryResult
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


app = FastAPI()

# Serve the Inngest endpoint
inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf])



# you can run the application by doing: uvicorn main:app
# you can then run inngest cli via: npx -y inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest