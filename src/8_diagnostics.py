import os
import streamlit as st
from services import azure_storage
from services import azure_oai


def check_azure_openai():
    """
    Returns True if the Azure OpenAI endpoint responds successfully to a test prompt, False otherwise.
    """

    try:
        oai_client = azure_oai.get_oai_client()
        response = oai_client.chat.completions.create(
            messages = [
                {
                    "role": "system",
                    "content": "Just return, 'Azure OpenAI connection works!'"
                },
                {
                    "role": "user",
                    "content": f"Reply as instructed"
                }
            ],
            model=azure_oai.AZURE_OPENAI_DEPLOYMENT_NAME
        )
        
        # If we successfully got a response back, let's assume it's working.
        if response.choices[0].message.content:
            return True, response.choices[0].message.content
        else:
            return False, "Azure OpenAI endpoint returned an unexpected response."
    except Exception as e:
        return False, f"Error calling Azure OpenAI endpoint: {str(e)}"


def check_azure_storage():
    """
    Returns True if we can connect to the Blob Storage account and list containers or blobs, False otherwise.
    """
    try:
        storage_account_name = azure_storage.STORAGE_ACCOUNT_NAME
        default_container = azure_storage.DEFAULT_CONTAINER

        if not storage_account_name or not default_container:
            return False, "Missing storage account name or default container in environment variables."

        # Check if main container exists by calling ensure_container_exists
        azure_storage.ensure_container_exists()
        azure_storage.list_blobs()
        
        # check queue access
        azure_storage.ensure_queue_exists()

    except Exception as e:
        error_message = str(e)
        
        if "AuthorizationFailure" in error_message:
            error_message += "\n\nMake sure you have Storage Blob Data Contributor and Storage Queue Data Contributor permission on the storage account."
            error_message += "\nAlso make sure your your Storage Account networking settings are correct."
        
        return False, f"Error connecting to Azure Blob Storage: {error_message}"
    return True, f"Successfully connected to container '{azure_storage.DEFAULT_CONTAINER}' and queue '{azure_storage.STORAGE_QUEUE_NAME}' in account '{azure_storage.STORAGE_ACCOUNT_NAME}'."

def check_local_config():
    """
    Returns True if the required environment variables are set, False otherwise.
    """
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "STORAGE_ACCOUNT_NAME",
        "AZURE_WHISPER_MODEL",
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_AUDIO_MODEL",
        "AZURE_OPENAI_DEPLOYMENT_NAME",
        "AZURE_OPENAI_EMBEDDING_MODEL"
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        return False, f"Missing required environment variables: {', '.join(missing_vars)}"
    
    optional_vars = [
        "DEFAULT_CONTAINER",
        "AUDIO_FOLDER",
        "TRANSCRIPTION_FOLDER",
        "EVAL_FOLDER",
        "LLM_ANALYSIS_FOLDER",
        "STORAGE_QUEUE_NAME",
        "AZURE_OPENAI_API_VERSION"
    ]
    
    # check all_vars, and create a list of incomplete_vars, which includes all vars that are not length 1 or longer
    incomplete_vars = [var for var in optional_vars if os.getenv(var) and len(os.getenv(var)) < 1]
    if incomplete_vars:
        return False, f"Incorrectly optional environment variables: {', '.join(incomplete_vars)}"
    
    return True, "All required environment variables are set."

def check_azure_search():
    ## check if the search endpoint is working
    try:
        index_client = azure_search.get_search_index_client()
        indexes = [i for i in index_client.list_indexes()]
        return True, f"Azure Search {azure_search.AZURE_SEARCH_ENDPOINT} is working."
    except Exception as e:
        return False, f"Error calling Azure Search: {str(e)}"


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

# Check Azure Storage connection
with st.expander("Check Azure Storage (Blob and Queue)", expanded=True):
    blob_ok, storage_message = check_azure_storage()
    if blob_ok:
        st.success(storage_message)
    else:
        st.error(storage_message)


# Check Azure Search
with st.expander("Check Azure Search", expanded=True):
    try:
        from services import azure_search
        search_ok, search_message = check_azure_search()
        if search_ok:
            st.success(search_message)
        else:
            st.error(search_message)
    except ImportError:
        st.error("Azure Search service not available. Please check the service implementation.")
    
    

