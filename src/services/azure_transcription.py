
from services import azure_oai
from dotenv import load_dotenv
from services import azure_storage
import os

load_dotenv()

def get_transcription_model():
    """Attempt to get config from azure_storage; return None on failure."""
    try:
        config = azure_storage.read_config()  # Should return a dict with keys like 'Transcription', 'LLM', etc.
        if config and "Transcription" in config:
            return config["Transcription"]
    except Exception:
        return  os.getenv("AZURE_WHISPER_MODEL")

transcription_model = get_transcription_model()
   
def parse_speakers_with_gpt4(transcribed_text: str) -> str:
    try:
        new_transcription = azure_oai.call_llm('./misc/clean_transcription.txt', transcribed_text)
        return new_transcription
    except Exception as e:
        print(f"Error cleaning transcription with 4o: {e}")
        return ""

def transcribe_audio(audio_path: str):
    # Step 1: Transcribe using Whisper or GPT-4-AUDIO
    try:
        #use azure_storage to download the blob from file_path to local storage and pass that to azure_oai
        transcription = ""
        audio_path = audio_path.replace(" ", "_")
        local_file = azure_storage.download_audio_to_local_file(audio_path)
        if transcription_model == "whisper":
            result = azure_oai.transcribe_whisper(local_file, prompt='./misc/whisper_prompt.txt')
            if len(result.text) == 0:
                return "Skipping due to transcription error."
            else:
                transcription = result.text

             # Step 2: Parse and label speakers with Azure OpenAI GPT-4
            parsed_conversation = parse_speakers_with_gpt4(transcription)
            if len(parsed_conversation) == 0:
                return "Skipping due to parsing error."
            
            return parsed_conversation
        else:
            result = azure_oai.transcribe_gpt4_audio(local_file)
            if len(result) == 0:
                return "Skipping due to transcription error."
            else:
                return result
          
    except Exception as e:
        print(f"Error transcribing {audio_path}: {e}")
        return f"Error transcribing {audio_path}: {e}"
   
