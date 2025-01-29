import os
import streamlit as st
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential

token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")    


def check_azure_openai():
    """
    Returns True if the Azure OpenAI endpoint responds successfully to a test prompt, False otherwise.
    """
    try:
        # Set up environment-based credentials for Azure OpenAI
        AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
        AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")  # Provide a default if needed

        AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

        oai_client = AzureOpenAI(
            api_version= AZURE_OPENAI_API_VERSION,
            azure_endpoint= AZURE_OPENAI_ENDPOINT,
            azure_ad_token_provider=token_provider
        )
   
        messages = [
        {
        "role": "system",
        "content": "You give time"
        },
        {
        "role": "user",
         "content": "what is the weather" }
        ]
        # Make a simple test call
        response = oai_client.chat.completions.create(
                messages=messages,
                model=AZURE_OPENAI_DEPLOYMENT_NAME,   
                temperature=0.2,
                top_p=1,
                max_tokens=5000,
                stop=None,
            )  

        # If we successfully got a response back, let's assume it's working.
        if response.choices[0].message.content:
            return True, response.choices[0].message.content
        else:
            return False, "Azure OpenAI endpoint returned an unexpected response."
    except Exception as e:
        return False, f"Error calling Azure OpenAI endpoint: {str(e)}"


def check_azure_blob():
    """
    Returns True if we can connect to the Blob Storage account and list containers or blobs, False otherwise.
    """
    try:
        storage_account_name = os.getenv("STORAGE_ACCOUNT_NAME")
        default_container = os.getenv("DEFAULT_CONTAINER")
        # Use DefaultAzureCredential for authentication

        credential = DefaultAzureCredential()

        if not storage_account_name or not default_container:
            return False, "Missing storage account name or default container in environment variables."

        # Create the BlobServiceClient object
        blob_service_client = BlobServiceClient(account_url=f"https://{storage_account_name}.blob.core.windows.net", credential=credential)

        # Attempt to get a container client and list blobs
        container_client = blob_service_client.get_container_client(default_container)
        _ = list(container_client.list_blobs())  # Just to test a simple operation

        return True, f"Successfully connected to container '{default_container}' in account '{storage_account_name}'."

    except Exception as e:
        return False, f"Error connecting to Azure Blob Storage: {str(e)}"


# Example for Cosmos DB check (uncomment and adjust credentials as needed)
# def check_azure_cosmos():
#     """
#     Returns True if we can connect to Cosmos DB and list databases, False otherwise.
#     """
#     try:
#         cosmos_endpoint = os.getenv("COSMOS_DB_ENDPOINT")

#         if not cosmos_endpoint:
#             return False, "Missing Cosmos DB endpoint in environment variables."

#         # Use DefaultAzureCredential for authentication
#         credential = DefaultAzureCredential()

#         # Initialize Cosmos client
#         client = CosmosClient(url=cosmos_endpoint, credential=credential)

#         # List databases (as a simple connectivity test)
#         databases = list(client.list_databases())
#         if databases:
#             return True, "Successfully connected to Cosmos DB. Databases found: " + ", ".join([db['id'] for db in databases])
#         else:
#             return True, "Successfully connected to Cosmos DB, but no databases found."
#     except Exception as e:
#         return False, f"Error connecting to Cosmos DB: {str(e)}"

def check_local_config():
    """
    Returns True if the required environment variables are set, False otherwise.
    """
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "STORAGE_ACCOUNT_NAME",
        "DEFAULT_CONTAINER",
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        return False, f"Missing environment variables: {', '.join(missing_vars)}"
    return True, "All required environment variables are set."

def check_local_misc_file():
    # check if .misc/clean_transcription.txt exists
    #check if .misc/whisper_prompt.txt exists

    if os.path.exists('./misc/clean_transcription.txt') and os.path.exists('./misc/whisper_prompt.txt'):
        return True, "All required files are present."
    else:
        return False, "Missing misc files, check the samples under ./misc folder."

st.title("Diagnostics Dashboard")
st.markdown("Use this page to check the connectivity and basic functionality of required services.")


# Check local environment variables
with st.expander("Check Local Configuration", expanded=True):
    config_ok, config_message = check_local_config()
    if config_ok:
        st.success(config_message)
    else:
        st.error(config_message)

# Check local misc files
with st.expander("Check Local Misc Files", expanded=True):
    misc_ok, misc_message = check_local_misc_file()
    if misc_ok:
        st.success(misc_message)
    else:
        st.error(misc_message)

# Check Azure OpenAI
with st.expander("Check Azure OpenAI Endpoint", expanded=True):
    openai_ok, openai_message = check_azure_openai()
    if openai_ok:
        st.success(openai_message)
    else:
        st.error(openai_message)

# Check Azure Blob Storage
with st.expander("Check Azure Blob Storage", expanded=True):
    blob_ok, blob_message = check_azure_blob()
    if blob_ok:
        st.success(blob_message)
    else:
        st.error(blob_message)

# Check Cosmos DB (uncomment once you’ve set up your environment variables and function)
# with st.expander("Check Azure Cosmos DB", expanded=True):
#     cosmos_ok, cosmos_message = check_azure_cosmos()
#     if cosmos_ok:
#         st.success(cosmos_message)
#     else:
#         st.error(cosmos_message)


# You can add more checks here for additional services,
# such as a separate Azure OpenAI mini-endpoint or others, using the same pattern.


