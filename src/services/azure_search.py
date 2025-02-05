import os
from services import azure_oai
import json
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
import re

from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SimpleField,
    SearchableField,
    SearchFieldDataType,
    SearchField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch,
    SearchIndex,
)

load_dotenv()

azure_credentials = DefaultAzureCredential()
# ------------------------------------------------------------------------------
# 1) Environment Variables / Constants
# ------------------------------------------------------------------------------
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
if not AZURE_SEARCH_ENDPOINT:
    raise ValueError("Please provide a valid Azure Search endpoint.")

AZURE_INDEX_NAME = os.getenv("AZURE_INDEX_NAME", "my-index")

# ------------------------------------------------------------------------------
# 2) Helpers to Flatten JSON and Infer Fields
# ------------------------------------------------------------------------------
def flatten_json(nested_json, parent_key="", sep="."):
    """
    Flatten JSON if there's only a single level of nesting.
    Example:
       {
         "sentiment": "great",
         "score": 2,
         "explanation": {
              "reason": "agent was helpful",
              "feedback": "awesome"
          }
       }
    -> {
         "sentiment": "great",
         "score": 2,
         "explanation.reason": "agent was helpful",
         "explanation.feedback": "awesome"
       }
    """
    items = []
    for k, v in nested_json.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_json(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def normalize_field_name(name: str) -> str:
    # Replace any character that is not a letter, digit, or underscore with an underscore.
    normalized = re.sub(r'[^A-Za-z0-9_]', '_', name)
    # Ensure the field name starts with a letter; if not, prefix it with "f_"
    if not re.match(r'^[A-Za-z]', normalized):
        normalized = "f_" + normalized
    return normalized

def infer_field_type(value):
    """
    Simple approach to map Python types to Azure Search field types.
    Adjust logic based on your requirements (e.g., for arrays, etc.).
    """
    if isinstance(value, bool):
        return SearchFieldDataType.Boolean
    elif isinstance(value, int):
        return SearchFieldDataType.Int64
    elif isinstance(value, float):
        return SearchFieldDataType.Double
    else:
        # For strings, lists, or anything else, store as string.
        # If you have lists, consider using Collection(Edm.String).
        return SearchFieldDataType.String


def build_dynamic_fields_from_json(flattened_json):
    """
    Given flattened JSON (key->value), build a list of Field objects
    to be used in the index definition.
    """
    fields = []
    # We will create a "dynamic" definition for each field we find.
    # We'll treat strings as `SearchableField` and numeric/bool as `SimpleField`.
    for k, v in flattened_json.items():
        normalized_key = normalize_field_name(k)
        field_type = infer_field_type(v)
        # If it's a string type, we can make it a 'SearchableField'
        if field_type == SearchFieldDataType.String:
            fields.append(SearchableField(name=normalized_key, type=field_type))
        else:
            # numeric or boolean
            fields.append(SimpleField(name=normalized_key, type=field_type, filterable=True, sortable=True))
    return fields


# ------------------------------------------------------------------------------
# 3) Create or Update the Index Dynamically
# ------------------------------------------------------------------------------
def create_or_update_index(index_name: str, sample_document: dict):
    """
    Create or update the index definition, pulling field names/types from a sample doc.
    """
    # Flatten the sample document (in case there's one-level nesting).
    flattened_sample = flatten_json(sample_document)

    # Build dynamic fields
    dynamic_fields = build_dynamic_fields_from_json(flattened_sample)

    # Always define a "key" field. We'll name it "id" here.
    key_field = SimpleField(name="id", type="Edm.String", key=True)

    # Define the embedding vector field
    vector_field = SearchField(
        name="contentVector",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        searchable=True,
        vector_search_dimensions=azure_oai.EMBEDDING_DIM,
        vector_search_profile_name="myHnswProfile"
    )

    # Also define a "content" field where we store full concatenated text
    # for semantic search and/or normal text queries
    content_field = SearchableField(name="content", type="Edm.String")

    # Final list of fields
    fields = [key_field] + dynamic_fields + [content_field, vector_field]

    # Vector search config
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(name="myHnsw")
        ],
        profiles=[
            VectorSearchProfile(
                name="myHnswProfile",
                algorithm_configuration_name="myHnsw",
            )
        ],
    )

    # Optional: semantic config
    semantic_config = SemanticConfiguration(
        name="my-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="id"),
            content_fields=[SemanticField(field_name="content")]
        )
    )
    semantic_search = SemanticSearch(configurations=[semantic_config])

    # Create the search index
    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search
    )

    # Create or update index
    try:
        search_index_client = SearchIndexClient(
            AZURE_SEARCH_ENDPOINT, 
            azure_credentials,
        )
        print(f"Creating or updating index '{index_name}'...")
        result = search_index_client.create_or_update_index(index)
        print(f"Index '{result.name}' created or updated.")
    except Exception as e:
        print(f"Failed to create/update the index: {e}")

# ------------------------------------------------------------------------------
# 4) Load JSON Docs and Upsert
# ------------------------------------------------------------------------------
def load_json_into_azure_search(index_name, json_docs):
    """
    Takes a list of JSON documents. For each:
      1) Flatten the JSON.
      2) Build an embedding manually via get_embedding().
      3) Upsert to Azure Search with 'contentVector'.
    """
    if not json_docs:
        print("No documents to process.")
        return

    # 6a) Create/Update the index with the first doc as a template
    sample_doc = json_docs[0]
    create_or_update_index(index_name, sample_doc)

    # 6b) Create a SearchClient
    search_client = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT, 
        index_name=index_name,
        credential=azure_credentials
    )

    # 6c) Convert each doc to final structure for upserting
    actions = []
    for i, doc in enumerate(json_docs):
        flattened = flatten_json(doc)
        doc_id = f"doc-{i}"

        # We'll build a 'content' string from all string fields
        text_parts = []
        for k, v in flattened.items():
            if isinstance(v, str):
                text_parts.append(v)
        combined_text = " ".join(text_parts) if text_parts else ""

        # Manually get embeddings
        embedding_vector = azure_oai.get_embedding(combined_text)

        # Prepare final doc
        final_doc = {
            "id": doc_id,
            "content": combined_text,
            "contentVector": embedding_vector
        }
        # Add flattened fields
        # Add flattened fields using normalized keys
        for k, v in flattened.items():
            normalized_key = normalize_field_name(k)
            # If the value is a list, join it into a string
            if isinstance(v, list):
                final_doc[normalized_key] = " ".join(map(str, v))
            else:
                final_doc[normalized_key] = v


        actions.append(final_doc)

    # 6d) Upsert in bulk
    try:
        results = search_client.upload_documents(documents=actions)
        print(f"Upserted {len(actions)} documents into index '{index_name}'.")
        return True
    except Exception as e:
        print(f"Failed to upload documents: {e}")
        return False

def search_query(index_name, query):
    """
    Search Azure Search index with a query string.
    """
    search_client = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT, 
        index_name=index_name,
        credential=azure_credentials
    )

    try:
        query_vector = azure_oai.get_embedding(query)

        # Execute a vector search with semantic ranking enabled.
        results = search_client.search(
            search_text="",
            vector_queries=[{"vector": query_vector, "fields": "contentVector", "k": 5,  "kind": "vector"}],
            query_type="semantic"
        )
        return list(results)
    except Exception as e:
        print(f"Search failed: {e}")
        return []
    
def index_exists(index_name):
    """
    Check if an index exists in Azure Search.
    """
    search_index_client = SearchIndexClient(
        endpoint=AZURE_SEARCH_ENDPOINT, 
        credential=azure_credentials
    )
    try:
        index = search_index_client.get_index(index_name)
        return index is not None
    except Exception as e:
        return False
# ------------------------------------------------------------------------------
# 7) Example Usage
# ------------------------------------------------------------------------------
if __name__ == "__main__":

    print(AZURE_SEARCH_ENDPOINT)
    with open("test.json", "r") as f:
        data = json.load(f)  # list of dicts
        print(data)

    load_json_into_azure_search(AZURE_INDEX_NAME, [data])