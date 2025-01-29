import os
import json

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

load_dotenv()

# Environment / configuration
STORAGE_ACCOUNT_NAME = os.getenv("STORAGE_ACCOUNT_NAME")
DEFAULT_CONTAINER = os.getenv("DEFAULT_CONTAINER", "mainproject")
AUDIO_FOLDER = os.getenv("AUDIO_FOLDER", "audios")
TRANSCRIPTION_FOLDER = os.getenv("TRANSCRIPTION_FOLDER", "transcriptions")
EVAL_FOLDER = os.getenv("EVAL_FOLDER", "evals")
PROMPT_FOLDER = os.getenv("PROMPT_FOLDER", "prompts")
LLM_ANALYSIS_FOLDER = os.getenv("LLM_ANALYSIS_FOLDER", "llmanalysis")

# Build URL to your blob storage & create credential + service client
account_url = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
credential = DefaultAzureCredential()
blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)


def ensure_container_exists(container_name: str = DEFAULT_CONTAINER):
    """
    Ensure the specified container exists; if not, create it.
    """
    try:
        container_client = blob_service_client.get_container_client(container_name)
        container_client.get_container_properties()
    except Exception as e:
        if "ContainerNotFound" in str(e):
            blob_service_client.create_container(container_name)
        else:
            raise e


def get_blob_client(blob_name: str, prefix: str = "", container_name: str = DEFAULT_CONTAINER):
    """
    Return the BlobClient for a given blob name and prefix within a container.
    """
    path = f"{prefix}/{blob_name}" if prefix else blob_name
    return blob_service_client.get_blob_client(container=container_name, blob=path)


def list_blobs(prefix: str = "", container_name: str = DEFAULT_CONTAINER):
    """
    List blobs within a container, optionally filtered by a prefix.
    Returns only the final part of the blob name (file name).
    """
    ensure_container_exists(container_name)
    container_client = blob_service_client.get_container_client(container_name)
    blob_list = container_client.list_blobs(name_starts_with=prefix)
    return [blob.name.split("/")[-1] for blob in blob_list]


def upload_blob(data, blob_name: str, prefix: str = "", container_name: str = DEFAULT_CONTAINER):
    """
    Upload the given data (file-like or bytes/string) to a blob name within a container/prefix.
    Overwrites if it exists.
    """
    if data is None:
        return "No data to upload."
    client = get_blob_client(blob_name, prefix, container_name)
    client.upload_blob(data, overwrite=True)
    return f"Uploaded file to: {prefix}/{blob_name}" if prefix else f"Uploaded file to: {blob_name}"


def download_blob_to_local_file(blob_name: str, prefix: str = "", local_path: str = None, overwrite: bool = False):
    """
    Download a blob to a local file path. If local_path is not provided,
    it defaults to using the same file name as the blob_name in the current directory.
    """
    if not local_path:
        local_path = blob_name  # Use blob_name as the default local file name

    directory = os.path.dirname(local_path)

    # Create the directory if it doesn't exist
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    if not overwrite and os.path.exists(local_path):
        return local_path

    client = get_blob_client(blob_name, prefix)
    # combine local working dir with local_path
    local_path = os.path.join(os.getcwd(), local_path)
    with open(local_path, "wb") as file_obj:
        download_stream = client.download_blob()
        file_obj.write(download_stream.readall())

    return local_path


def read_blob(blob_name: str, prefix: str = ""):
    """
    Read blob content as text (UTF-8).
    """
    try:
        client = get_blob_client(blob_name, prefix)
        download_stream = client.download_blob()
        return download_stream.readall().decode("utf-8")
    except Exception as e:
        print(f"Error reading blob: {e}")
        return None


def delete_blob(blob_name: str, prefix: str = ""):
    """
    Delete a blob from the container/prefix.
    """
    client = get_blob_client(blob_name, prefix)
    client.delete_blob()
    return f"Deleted blob: {prefix}/{blob_name}" if prefix else f"Deleted blob: {blob_name}"


def update_blob(blob_name: str, updated_content, prefix: str = ""):
    """
    Overwrite a blob with new text/binary content.
    """
    return upload_blob(updated_content, blob_name, prefix)


# ----------------------------------------------------------------------------
# Convenience functions for specific folders
# ----------------------------------------------------------------------------

def list_audios():
    return list_blobs(AUDIO_FOLDER)


def list_evals(prompt_name):
    """
    List all JSON evals under /EVAL_FOLDER/<prompt_no_ext>/
    """
    prompt_no_ext = prompt_name.split('.')[0]
    prefix = f"{EVAL_FOLDER}/{prompt_no_ext}"
    return list_blobs(prefix)

def list_transcriptions():
    return list_blobs(TRANSCRIPTION_FOLDER)

def list_prompts():
    all_prompts = list_blobs(PROMPT_FOLDER)
    # Filter out config files
    return [p for p in all_prompts if "__config" not in p]


def upload_audio_to_blob(file):
    # file should be an open file-like object or an UploadFile (FastAPI, etc.)
    name_no_spaces = file.name.replace(" ", "_")
    return upload_blob(file, name_no_spaces, AUDIO_FOLDER)

def upload_prompt_to_blob(file):
    return upload_blob(file, file.name, PROMPT_FOLDER)


    
def download_audio_to_local_file(blob_name):
    return download_blob_to_local_file(blob_name, AUDIO_FOLDER, "./tmp/" + blob_name)

def delete_audio(blob_name):
    return delete_blob(blob_name, AUDIO_FOLDER)

def read_transcription(blob_name):
    return read_blob(blob_name, TRANSCRIPTION_FOLDER)

def delete_transcription(blob_name):
    return delete_blob(blob_name, TRANSCRIPTION_FOLDER)

def read_prompt(blob_name):
    return read_blob(blob_name, PROMPT_FOLDER)

def update_prompt(blob_name, updated_content):
    return update_blob(blob_name, updated_content, PROMPT_FOLDER)

def upload_transcription_to_blob(blob_name, transcribed_text):
    """
    Upload a transcription as a .txt file in the TRANSCRIPTION_FOLDER.
    """
    # Clean up any spaces, etc.
    transcription_file_name = blob_name.split('/')[-1].replace(" ", "_") + ".txt"
    return upload_blob(transcribed_text, transcription_file_name, TRANSCRIPTION_FOLDER)


def transcription_already_exists(blob_name: str):
    """
    Check if a transcription for `blob_name` (as .txt) already exists.
    """
    transcription_file_name = blob_name + ".txt"
    return transcription_file_name in list_blobs(TRANSCRIPTION_FOLDER)


def get_calls_to_transcribe():
    calls = list_audios()
    total_calls = len(calls)
    total_transcribed = 0
    call_to_be_transcribed = []
    for call in calls:
        call_id = call.split('.')[0]
        if transcription_already_exists(call_id):
            total_transcribed += 1
        else:
            call_to_be_transcribed.append(call_id)

    return call_to_be_transcribed, total_transcribed, total_calls
# ----------------------------------------------------------------------------
# Prompt config helpers
# ----------------------------------------------------------------------------

def upload_prompt_config(prompt_name, config):
    """
    Upload a JSON config for a given prompt. The config blob name is <prompt_no_ext>__config.json
    """
    config_blob_name = prompt_name.split('.')[0] + "__config.json"
    data_to_upload = json.dumps(config)
    return upload_blob(data_to_upload, config_blob_name, PROMPT_FOLDER)


def read_prompt_config(blob_name):
    """
    Read the JSON config for a given prompt (if it exists).
    """
    config_blob_name = blob_name.split('.')[0] + "__config.json"
    try:
        content = read_blob(config_blob_name, PROMPT_FOLDER)
        return json.loads(content)
    except Exception:
        return None

def read_config():
    """
    Read the JSON config for transcription models or LLMs ect..
    """
    config_blob_name = "app_config.json"
    try:
        content = read_blob(config_blob_name, None)
        return json.loads(content)
    except Exception:
        return None

def save_config(config):
    """
    Save the JSON config for transcription models or LLMs ect..
    """
    config_blob_name = "app_config.json"
    data_to_upload = json.dumps(config)
    return upload_blob(data_to_upload, config_blob_name, "")
# ----------------------------------------------------------------------------
# LLM Analysis Listing/Reading
# ----------------------------------------------------------------------------

def list_llmanalysis(prompt_name):
    """
    List all JSON analyses under /LLM_ANALYSIS_FOLDER/<prompt_no_ext>/
    """
    prompt_no_ext = prompt_name.split('.')[0]
    prefix = f"{LLM_ANALYSIS_FOLDER}/{prompt_no_ext}"
    return list_blobs(prefix)


def read_llm_analysis(prompt_name: str, file_name: str) -> dict:
    """
    Load an LLM analysis file (JSON) from the container.
    """
    prompt_no_ext = prompt_name.split('.')[0]
    prefix = f"{LLM_ANALYSIS_FOLDER}/{prompt_no_ext}"
    try:
        content = read_blob(file_name, prefix)
        return json.loads(content)
    except:
        return {}

def read_eval(prompt_name: str, file_name: str) -> dict:
    """
    Load an LLM analysis file (JSON) from the container.
    """
    prompt_no_ext = prompt_name.split('.')[0]
    prefix = f"{EVAL_FOLDER}/{prompt_no_ext}"
    try:
        content = read_blob(file_name, prefix)
        return json.loads(content)
    except:
        return {}

def upload_llm_analysis_to_blob(name, prompt, analysis):
    """
    For storing analysis in JSON under /LLM_ANALYSIS_FOLDER/<prompt_name>/<name_no_ext>.json
    """
    prompt_name_no_ext = prompt.split('.')[0]
    call_id = name.split('.')[0]
    analysis_path = f"{prompt_name_no_ext}/{call_id}.json"
    full_prefix = LLM_ANALYSIS_FOLDER

    try:
        # Convert `analysis` to JSON if it's a Python dict
        data_to_upload = analysis if isinstance(analysis, str) else json.dumps(analysis)
        return upload_blob(data_to_upload, analysis_path, full_prefix)
    except Exception as e:
        return f"An error occurred while uploading LLM analysis: {e}"

def upload_eval_to_blob(name, prompt, evaluation):
    """
    For storing evals in JSON under /EVAL_FOLDER/<prompt_name>/<name_no_ext>.json
    """
    prompt_name_no_ext = prompt.split('.')[0]
    call_id = name.split('.')[0]
    eval_path = f"{prompt_name_no_ext}/{call_id}.json"
    full_prefix = EVAL_FOLDER

    try:
        # Convert `analysis` to JSON if it's a Python dict
        data_to_upload = evaluation if isinstance(evaluation, str) else json.dumps(evaluation)
        return upload_blob(data_to_upload, eval_path, full_prefix)
    except Exception as e:
        return f"An error occurred while uploading eval: {e}"