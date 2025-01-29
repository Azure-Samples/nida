from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
import uuid
import os

# Load environment variables
load_dotenv()

def upload_prompt(prompt_file, prompt_description):
    # Create a credential object
    credential = DefaultAzureCredential()

    prompt_content = prompt_file.read().decode("utf-8")
            
    # Create a unique ID for the document
    document_id = str(uuid.uuid4())
    
    # Create a document to insert into Cosmos DB
    document = {
        "id": document_id,
        "content": prompt_content,
        "filename": prompt_file.name,
        "description": prompt_description
    }
    
    # Insert the document into Cosmos DB
    COSMOS_DB_ENDPOINT = os.getenv("COSMOS_DB_ENDPOINT")
    cosmos_client = CosmosClient(COSMOS_DB_ENDPOINT, credential=credential)
    database_name = os.getenv("COSMOS_DB_DATABASE_NAME")
    container_name = os.getenv("COSMOS_DB_CONTAINER_NAME")
    database = cosmos_client.get_database_client(database_name)
    container = database.get_container_client(container_name)
    # Check if the database exists, if not create it
    try:
        database = cosmos_client.create_database_if_not_exists(id=database_name)
    except Exception as e:
        return f"Failed to create or access database: {str(e)}"
    
    # Check if the container exists, if not create it
    try:
        container = database.create_container_if_not_exists(
            id=container_name,
            partition_key=PartitionKey(path="/id")
        )
    except Exception as e:
        return f"Failed to create or access container: {str(e)}"
    container.create_item(document)
    return f"Uploaded prompt file to Cosmos DB with ID: {document_id}"

def list_prompts():
    # Create a credential object
    credential = DefaultAzureCredential()
    
    # Get the Cosmos DB endpoint
    COSMOS_DB_ENDPOINT = os.getenv("COSMOS_DB_ENDPOINT")
    
    # Create a Cosmos DB client
    cosmos_client = CosmosClient(COSMOS_DB_ENDPOINT, credential=credential)
    
    # Get the database and container
    database_name = os.getenv("COSMOS_DB_DATABASE_NAME")
    container_name = os.getenv("COSMOS_DB_CONTAINER_NAME")

    try:
        database = cosmos_client.create_database_if_not_exists(id=database_name)
    except Exception as e:
        return f"Failed to create or access database: {str(e)}"
    
    # Check if the container exists, if not create it
    try:
        container = database.create_container_if_not_exists(
            id=container_name,
            partition_key=PartitionKey(path="/id")
        )
    except Exception as e:
        return f"Failed to create or access container: {str(e)}"
    
   
    # Query for all items in the container
    query = "SELECT * FROM c"
    items = list(container.query_items(query, enable_cross_partition_query=True))
    
    # Return a list of filenames
    return [item["filename"] for item in items]