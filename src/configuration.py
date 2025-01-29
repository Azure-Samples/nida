import os
import streamlit as st
from dotenv import load_dotenv

from services import azure_storage  

def save_new_config(selection):
    """
    Save the new transcription model selection to azure_storage.
    In this example, we only update 'Transcription'. If you need
    to update other fields (like 'LLM'), adjust accordingly.
    """
    config_dict = {
        "Transcription": selection,
    }
    azure_storage.save_config(config_dict)


def load_saved_config():
    """Attempt to get config from azure_storage; return None on failure."""
    try:
        return azure_storage.read_config()  # Should return a dict with keys like 'Transcription', 'LLM', etc.
    except Exception as e:
        print(f"Error loading config from azure_storage. {e}")
        return None

    
st.title("🎧 Application Configuration")
st.markdown(
    """Select your preferred **transcription** model from the options below.
    
    """
)

# 1. Load config from azure_storage
config_data = load_saved_config()

# 2. Load .env to ensure environment variables are available
load_dotenv()

# Read the environment variables
default_whisper = os.getenv("AZURE_WHISPER_MODEL")    # Must be set
default_audio   = os.getenv("AZURE_AUDIO_MODEL", "")   # Optional

# We'll provide two “display” options in the dropdown
model_options = [default_whisper]

if default_audio != "":
    model_options.append(default_audio)

if config_data and "Transcription" in config_data:
    current_selection = config_data["Transcription"]
else:
    current_selection = default_whisper

#check if the current selection is in the model options
if current_selection not in model_options:
    current_selection = default_whisper

# 4. Render the selectbox with the final "current_selection" as default
selected_model = st.selectbox(
    "Choose a transcription model:",
    model_options,
    index=model_options.index(current_selection)
)


# 5. Button to save the new selection
if st.button("Save Config"):
    save_new_config(selected_model)
    st.success(f"Configuration saved! (Transcription = '{selected_model}')")

st.markdown("---")
st.subheader("Your Selection")
st.write(f"**Transcription Model:** {selected_model}")

# Show extra info about environment variables for clarity
st.markdown("---")
