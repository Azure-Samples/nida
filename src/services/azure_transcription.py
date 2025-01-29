
from services import azure_oai
from dotenv import load_dotenv
from services import azure_storage

load_dotenv()


def transcribe_audio_with_whisper(file_path: str) -> str:
    try:
        #use azure_storage to download the blob from file_path to local storage and pass that to azure_oai
        file_path = file_path.replace(" ", "_")
        local_file = azure_storage.download_audio_to_local_file(file_path)
        transcript = azure_oai.transcribe(local_file, prompt='./misc/whisper_prompt.txt')
        return transcript.text
    except Exception as e:
        print(f"Error transcribing {file_path}: {e}")
        return f"Error transcribing {file_path}: {e}"

def parse_speakers_with_gpt4(transcribed_text: str) -> str:
    try:
        new_transcription = azure_oai.call_llm('./misc/clean_transcription.txt', transcribed_text)
        return new_transcription
    except Exception as e:
        print(f"Error cleaning transcription with 4o: {e}")
        return ""

def transcribe_audio(audio_path: str):
    # Step 1: Transcribe using Whisper
    transcription = transcribe_audio_with_whisper(audio_path)
    if  len(transcription) == 0:
        return "Skipping due to transcription error."

    # Step 2: Parse and label speakers with Azure OpenAI GPT-4
    parsed_conversation = parse_speakers_with_gpt4(transcription)
    if len(parsed_conversation) == 0:
        return "Skipping due to parsing error."
    
    return parsed_conversation
