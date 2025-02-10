import os
import json

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.storage.queue import QueueClient

load_dotenv()

# Environment / configuration
STORAGE_ACCOUNT_NAME = os.getenv("STORAGE_ACCOUNT_NAME")
if not STORAGE_ACCOUNT_NAME:
    raise ValueError("Missing STORAGE_ACCOUNT_NAME in environment variables.")

DEFAULT_QUEUE = os.getenv("DEFAULT_CONTAINER", "integration-queue")
LLM_ANALYSIS_FOLDER = os.getenv("LLM_ANALYSIS_FOLDER", "llmanalysis")

# Build URL to your blob storage & create credential + service client
account_url = f"https://{STORAGE_ACCOUNT_NAME}.queue.core.windows.net"
credential = DefaultAzureCredential()
# Removed queue_service_client as it is not used; use get_queue_client to create QueueClient per queue.


def ensure_queue_exists(queue_name: str):
    """
    Ensure the specified queue exists. Creates it if it does not.
    """
    queue_client = QueueClient(account_url=account_url, credential=credential, queue_name=queue_name)
    try:
        queue_client.create_queue()
    except Exception:
        # The queue may already exist
        pass

def get_queue_client(queue_name: str = DEFAULT_QUEUE):
    """
    Return the QueueClient for the given queue name, ensuring it exists.
    """
    ensure_queue_exists(queue_name)
    return QueueClient(account_url=account_url, credential=credential, queue_name=queue_name)

def send_message_to_queue(message: str, queue_name: str = DEFAULT_QUEUE):
    """
    Send a message to the specified queue.
    """
    queue_client = get_queue_client(queue_name)
    response = queue_client.send_message(message)
    return f"Sent message to queue '{queue_name}' with message id: {response.id}"


