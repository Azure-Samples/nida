import azure.functions as func
import logging
import os
import json

from dotenv import load_dotenv
load_dotenv(override=True)

app = func.FunctionApp()

import logging
logger = logging.getLogger(__name__)

DEFAULT_CONTAINER = os.getenv("DEFAULT_CONTAINER")

STORAGE_QUEUE_NAME = os.getenv("STORAGE_QUEUE_NAME", "integration-queue")

@app.blob_trigger(arg_name="myblob", path=DEFAULT_CONTAINER +"/{blobname}", connection="AzureWebJobsStorage")
@app.queue_output(arg_name="outputQueue", queue_name=STORAGE_QUEUE_NAME, connection="AzureWebJobsStorage")
def process_blob(myblob: func.InputStream, blobname: str, outputQueue: func.Out[str]):

    logging.info(f"Processing blob: {blobname} with size {myblob.length} bytes.")

    metadata = {
        "blob_name": blobname,
        "blob_size": myblob.length,
        "event": "created_or_updated"
    }

    outputQueue.set(json.dumps(metadata))