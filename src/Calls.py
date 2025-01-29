
import streamlit as st
from services import azure_storage, azure_transcription

# ------------------------ MAIN APP LAYOUT ------------------------ #

# Add a sidebar for quick navigation or info
st.sidebar.title("ℹ️ About This App")
st.sidebar.write(
    "This application allows you to **upload**, **manage**, **transcribe**, and **analyze** audio files using Azure Storage and LLM-based analysis."
)
st.sidebar.markdown("---")
st.sidebar.markdown("**Navigation**")
st.sidebar.markdown("1. Calls\n2. Personas\n3. GenAI Analysis")

# 1. Upload Files
st.header("1. 🎧 Upload Files")
st.markdown("Use the sections below to upload your audio files. All uploads are stored in Azure Blob Storage.")

audio_files = st.file_uploader("Choose audio files", type=["wav", "mp3", "m4a"], accept_multiple_files=True)
if st.button("Upload & Transcribe File(s)", key="upload_audio"):
    if audio_files:
        
        with st.spinner("Uploading and running transcriptions..."):
            info_box = st.empty()
            for audio_file in audio_files:
                info_box.info(azure_storage.upload_audio_to_blob(audio_file))
                info_box.info(f"Transcribing  **{audio_file.name}** ...")
                transcript = azure_transcription.transcribe_audio(audio_file.name)            
                name_no_ext = audio_file.name.split(".")[0]
                azure_storage.upload_transcription_to_blob(name_no_ext, transcript)
                info_box.info(f"Transcription for **{audio_file.name}** uploaded successfully.")
        st.success("All audio files uploaded successfully.", icon="✅")
    else:
        st.error("No audio files selected.")
    

st.markdown("---")

# 2. Manage Existing Files
st.header("2. Manage Existing Calls")
blobs = azure_storage.list_audios()
if not blobs:
    st.info("No audio files found.")
else:
    for blob_name in blobs:
        name_only = blob_name.rsplit(".")[0]
        
        with st.expander(f"📞 {blob_name}"):
            # Add an audio player if you’d like
            audio_file = azure_storage.download_audio_to_local_file(blob_name)
            st.audio(audio_file, format="audio/mp3")  # or the correct format

            # Show transcript
            transcript_name = f"{name_only}.txt"
            transcript = azure_storage.read_transcription(transcript_name)
            if transcript:
                st.markdown(transcript)
            else:
                st.write("Transcript not found.")

            # Delete button
            if st.button("Delete", key=f"delete_{blob_name}"):
                outcome = azure_storage.delete_audio(blob_name)
                azure_storage.delete_transcription(transcript_name)
                st.success(outcome)

# Optional: a nice footer or credits
st.write("")
st.markdown("<hr style='border: 1px solid #ddd;' />", unsafe_allow_html=True)
st.caption("© 2025 Contoso - Built with Azure AI Services")
