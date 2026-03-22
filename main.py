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

load_dotenv()

# Create an Inngest client
inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
    serializer=inngest.PydanticSerializer()
)

# Create an Inngest function
@inngest_client.create_function(
    fn_id="TrialFunction",
    trigger=inngest.TriggerEvent(event="app/my_function"),
)
async def my_function(ctx: inngest.Context) -> str:
    ctx.logger.info(ctx.event)
    return "done"

app = FastAPI()

# Serve the Inngest endpoint
inngest.fast_api.serve(app, inngest_client, [my_function])



# you can run the application by doing: uvicorn main:app
# you can then run inngest cli via: npx cli@latest dev -u http://127.0.0.1:8000/api/inngest
