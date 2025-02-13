import os
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
import re

import base64

load_dotenv()

token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")    

AZURE_OPENAI_ENDPOINT=os.getenv("AZURE_OPENAI_ENDPOINT")
if not AZURE_OPENAI_ENDPOINT:
    raise ValueError("AZURE_OPENAI_ENDPOINT is not set.")

AZURE_OPENAI_DEPLOYMENT_NAME=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"]
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-11-01-preview")

AZURE_WHISPER_MODEL=os.environ["AZURE_WHISPER_MODEL"]
AZURE_AUDIO_MODEL=os.getenv("AZURE_AUDIO_MODEL", "")

AZURE_OPENAI_EMBEDDING_MODEL = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL")
if (AZURE_OPENAI_EMBEDDING_MODEL == 'text-embedding-ada-002'):
    EMBEDDING_DIM = 1536    # For text-embedding-ada-002
elif (AZURE_OPENAI_EMBEDDING_MODEL == 'text-embedding-3-large'):
    EMBEDDING_DIM = 3072    # For text-embedding-3-large

def get_oai_client():
    oai_client = AzureOpenAI(
        api_version= AZURE_OPENAI_API_VERSION,
        azure_endpoint= AZURE_OPENAI_ENDPOINT, 
        azure_ad_token_provider=token_provider
    )
    return oai_client

def build_o1_prompt(prompt_file, transcript):
    
    if prompt_file is None:
        return "No prompt file provided"
    else:
        system_prompt = open(prompt_file, "r").read()   

    messages = [
        {
        "role": "user",
        "content": system_prompt
        },
        {
        "role": "user",
         "content": (f"Here is the transcript:\n\n {transcript}") }
    ]
      
    return messages

def build_prompt(prompt, transcript):
    
    if prompt is None:
        return "No prompt file provided"
    elif prompt.endswith(".txt"):
        system_prompt = open(prompt, "r").read()
    else:
        system_prompt = prompt  

    messages = [
        {
        "role": "system",
        "content": system_prompt
        },
        {
        "role": "user",
         "content": (f"Here is the transcript:\n\n {transcript}") }
    ]
      
    return messages

def call_o1(prompt_file, transcript, deployment):
    messages = build_o1_prompt(prompt_file=prompt_file, transcript=transcript)  

    oai_client = get_oai_client()

    completion = oai_client.chat.completions.create(
        model=deployment,   
        messages=messages,
    )  

    return clean_json_string(completion.choices[0].message.content)

def call_llm(prompt, transcript, deployment=AZURE_OPENAI_DEPLOYMENT_NAME, response_format=None):

    messages = build_prompt(prompt=prompt, transcript=transcript)  

    oai_client = get_oai_client()
   
    if response_format is not None:
        result = oai_client.beta.chat.completions.parse(model=deployment, 
                                                            temperature=0.2, 
                                                            messages=messages, 
                                                            response_format=response_format)
        
        return result.choices[0].message.parsed
    else:
        completion = oai_client.chat.completions.create(
            messages=messages,
            model=deployment,
            temperature=0.2,
            top_p=1,
            max_tokens=5000,
            stop=None,
        )

        return clean_json_string(completion.choices[0].message.content)

def clean_json_string(json_string):
    pattern = r'^```json\s*(.*?)\s*```$'
    cleaned_string = re.sub(pattern, r'\1', json_string, flags=re.DOTALL)
    return cleaned_string.strip()

def transcribe_whisper(audio_file, prompt):
    oai_client = get_oai_client()
   
    prompt_content =open(prompt, "r").read()
    result = oai_client.audio.transcriptions.create(
        file=open(audio_file, "rb"),   
        prompt=prompt_content,         
        model=AZURE_WHISPER_MODEL
    )
    
    return result

def transcribe_gpt4_audio(audio_file):
    oai_client = get_oai_client()
   
    print(f"Transcribing with gpt-4o-audio {audio_file}")
    file = open(audio_file, "rb")
    encoded_string = base64.b64encode(file.read()).decode('utf-8')
    file.close()

    messages=[
        {
            "role": "user",
            "content": [
                { 
                    "type": "text",
                    "text": "Transcribe the audio as is. no explanation needed. If you are able to detect the agent versus the customer, please label them as such. use **Customer:** and **Agent:** to label the speakers."
                },
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": encoded_string,
                        "format": "wav"
                    }
                }
            ]
        },
    ]

    completion = oai_client.chat.completions.create(
        model=AZURE_AUDIO_MODEL,
        modalities=["text"],
        messages=messages
    )

    return completion.choices[0].message.content


def get_embedding(query_text):
    oai_emb_client = AzureOpenAI(
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        azure_ad_token_provider=token_provider
    )

    response = oai_emb_client.embeddings.create(
        model=AZURE_OPENAI_EMBEDDING_MODEL,
        input=[query_text]  # input must be a list
    )

    return response.data[0].embedding

def chat_with_oai(messages, deployment=AZURE_OPENAI_DEPLOYMENT_NAME):

    oai_client = get_oai_client()
   
    completion = oai_client.chat.completions.create(
        messages=messages,
        model=deployment,   
        temperature=0.2,
        top_p=1,
        stream=True,
        max_tokens=5000,
        stop=None,
    )  

      # Iterate over the streamed response
    for chunk in completion:
        # Access the first choice from the chunk.
        # Since `chunk` is a Pydantic model, use attribute access instead of .get()
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta  # delta is also a Pydantic model
        # Get the content if available
        content = delta.content if delta and hasattr(delta, "content") else ""
        if content:
            yield content

def get_insights(summaries):

    system_prompt = """
    you will be provided with different call summaries, your task is to analyze all the summaries, and return key insights.

    What are the main topics? Issues? Insights and recommendations

    """
    oai_client = get_oai_client()
    
    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ] + [
        {
            "role": "user",
            "content": f"call: {call} \n\n"
        } for call in summaries
    ]
      

    completion = oai_client.chat.completions.create(
        messages=messages,
        model=AZURE_OPENAI_DEPLOYMENT_NAME,   
        temperature=0.2,
        top_p=1,
        max_tokens=5000,
        stop=None,
    )  

    return completion.choices[0].message.content
