import os
from dotenv import load_dotenv
import streamlit as st
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from functools import lru_cache
from azure.ai.agents.models import ListSortOrder

# Detect local vs deployed
def is_local():
    return os.environ.get("LOCAL_DEV") == "1" or os.path.exists(".env")

if is_local():
    load_dotenv()


@st.cache_resource
def get_secret_client():
    credential = DefaultAzureCredential()  # uses Managed Identity in Azure; dev uses az login, VS Code, etc.
    vault_url = os.environ["key-vault-url"]
    return SecretClient(vault_url=vault_url, credential=credential)

#cache secret to avoid frequent lookups, allow for rotation
@lru_cache(maxsize=64)
def _get_secret_no_ttl(name, version=None):
    client = get_secret_client()
    if version:
        return client.get_secret(name, version=version).value
    return client.get_secret(name).value

def get_secret(name, version=None, force_refresh=False):
    if is_local():
        # Load from .env or environment variable
        return os.environ.get(name)
    else:
        # Load from Azure Key Vault
        if force_refresh:
            _get_secret_no_ttl.cache_clear()
        return _get_secret_no_ttl(name, version)
    
#####################################
def create_thread(client, agent_id, user_message):
    thread = client.agents.threads.create()
    client.agents.messages.create(
        thread_id=thread.id, 
        role="user", 
        content=user_message
    )
    run = client.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent_id)
    if run.status == "failed":
        st.error(f"Run failed: {run.last_error}")
        return None, None
    return thread.id, run.id

def get_responses(client, thread_id, run_id):
    messages = client.agents.messages.list(thread_id=thread_id, order=ListSortOrder.ASCENDING)
    responses = []
    for message in messages:
        if message.run_id == run_id and message.text_messages:
            responses.append(f"{message.role}: {message.text_messages[-1].text.value}")
    return responses 

def main():
    st.title("AI Dinner Planning Agent")

    client = AIProjectClient(
        #endpoint=st.secrets["api"]["azure_endpoint"],
        endpoint=get_secret("dingen-azure-endpoint"),
        credential=DefaultAzureCredential(),
    )
    agent_id = st.secrets["api"]["agent_id"]


    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []

    user_input = st.chat_input("Enter your message...")

    if user_input:
        # Display user message in chat
        #st.chat_message("user").markdown(user_input)
        st.session_state['chat_history'].append(('user', user_input))

        # Send user message to agent and get a response
        thread_id, run_id = create_thread(client, agent_id, user_input)
        if thread_id and run_id:
            responses = get_responses(client, thread_id, run_id)
            for response in responses:
                # Append response to chat history
                st.session_state['chat_history'].append(('assistant', response))
            # Display chat history
            for role, message in st.session_state['chat_history']:
                if role == 'user':
                    st.chat_message("user").markdown(message)
                else:
                    st.chat_message("assistant").markdown(message)

if __name__ == "__main__":
    main()