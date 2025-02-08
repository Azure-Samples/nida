import streamlit as st

try:
    from services import azure_storage, azure_search, azure_oai
except ValueError as e:
    st.markdown(f"""
    <div style="border: 1px solid #ff4d4f; padding: 10px; border-radius: 5px; background-color: var(--color-bg-primary)">
      <h4 style="margin: 0;">⚠️ Missing Environment Variables</h4>
      <p style="margin: 5px 0 0;">Please set the required ENV variables before running the application.</p>
      <p style="font-style: italic; margin: 5px 0 0;">Error details: <code>{e}</code></p>
    </div>
    """, unsafe_allow_html=True)
    # Optionally, stop further execution:
    st.stop()



def build_system_prompt(persona, provided_context):
    """
    Build the system prompt message that is sent to the assistant.

    Args:
        persona (str): The persona context read from the selected prompt file.
        provided_context (str): The additional context (e.g., search results).

    Returns:
        str: The formatted system prompt.
    """
    system_prompt_template = """
    You are a helpful assistant that helps users understand their calls.
    You will be provided with calls from a LLM analysis, along with a query, 
    and your task is to help the user understand the call.

    The calls were analyzed using the prompt below, provided as context to help 
    guide your understanding of the call.

    ## PROMPT CONTEXT
    {persona_context}

    ## END PROMPT CONTEXT

    And the query returned the following context:

    ## PROVIDED CONTEXT
    {context}
    ## END PROVIDED CONTEXT

    Reply in normal text format.
    """
    return system_prompt_template.format(
        persona_context=persona, 
        context=provided_context
    )


def load_llm_analysis(prompt_file):
    """
    Load LLM analysis JSON documents from Azure Storage.

    Args:
        prompt_file (str): The filename used to fetch the analysis documents.

    Returns:
        list: A list of JSON documents.
    """
    llm_analysis = azure_storage.list_llmanalysis(prompt_file)
    all_jsons = []
    if llm_analysis:
        for file in llm_analysis:
            try:
                data = azure_storage.read_llm_analysis(prompt_file, file)
                all_jsons.append(data)
            except Exception as e:
                st.error(f"❌ Error reading {file}: {e}")
    return all_jsons


# ---------------- Sidebar: Prompt Selection and Index Creation ----------------
st.header("👤 Chat with your calls")

# List all persona (.txt) files available in the container.
all_prompt_files = azure_storage.list_prompts()

if not all_prompt_files:
    st.error("⚠️ No persona files found in Blob Storage.")
    st.stop()

# Allow the user to select a persona file from the sidebar.
selected_prompt_txt = st.selectbox("Select Persona:", all_prompt_files)

# Clear chat history if the selected prompt has changed.
if "selected_prompt_txt_prev" in st.session_state and st.session_state.selected_prompt_txt_prev != selected_prompt_txt:
    st.session_state.messages = []

st.session_state.selected_prompt_txt_prev = selected_prompt_txt

# Read the selected persona prompt and set it as context.
persona_context = azure_storage.read_prompt(selected_prompt_txt)

# When the user clicks the button, load the JSON docs and create/re-index the search index.
if st.button("🗂️ Index Your Calls"):
    index_name = selected_prompt_txt.split('.')[0]
    if azure_search.index_exists(index_name):
        if st.button(f"🔄 Index '{index_name}' exists. Click to re-index."):
            all_jsons = load_llm_analysis(selected_prompt_txt)
            if not all_jsons:
                st.warning("⚠️ No analysis documents found for re-indexing.")
            else:
                azure_search.load_json_into_azure_search(index_name, all_jsons)
                st.success(f"✅ Index '{index_name}' re-indexed successfully.")
        else:
            st.info(f"ℹ️ Using existing index '{index_name}'.")
    else:
        all_jsons = load_llm_analysis(selected_prompt_txt)
        if not all_jsons:
            st.warning("⚠️ No analysis documents found for indexing.")
        else:
            message, created = azure_search.load_json_into_azure_search(index_name, all_jsons)
            if created:
                st.success(f"✅ Index '{index_name}' created successfully.")
            else:
                st.error(f"❌ Error creating index '{message}'.")


# ---------------- Chat Area ----------------
st.header("💬 Chat with Calls")

# Initialize the chat history if not already present.
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display the conversation history using Streamlit's chat message components.
for message in st.session_state.messages:
    # 'role' can be "user", "assistant", or "system".
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Use Streamlit's chat input (requires Streamlit 1.23+).
user_input = st.chat_input("Type your query here...")

if user_input:
    # Append and display the user message.
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Determine the index name based on the selected prompt.
    index_name = selected_prompt_txt.split('.')[0]

    # ---------------- Query the Azure AI Search Index ----------------
    # Fetch documents that are relevant to the user's query.
    relevant_docs = azure_search.search_query(index_name, user_input)

    # Build a system context using the persona and the search results.
    system_context = build_system_prompt(persona_context, relevant_docs)

    # Combine the conversation history with the system context.
    combined_context = st.session_state.messages.copy()
    combined_context.append({"role": "system", "content": system_context})

    # ---------------- Call Azure OpenAI LLM with Streaming ----------------
    response_stream = azure_oai.chat_with_oai(combined_context)
    full_response = ""
    with st.chat_message("assistant"):
    # Create an empty placeholder to update the markdown continuously
        message_placeholder = st.empty()
        for chunk in response_stream:
            full_response += chunk
            # Update the same markdown element each time
            message_placeholder.markdown(full_response)
    st.session_state.messages.append({"role": "assistant", "content": full_response})
