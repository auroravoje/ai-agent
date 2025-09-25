import os
from typing import Optional, Tuple, List, Any
from dotenv import load_dotenv
import streamlit as st
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder
from streamlit_styles import apply_style_background, apply_style_blur

# Detect local vs deployed
def is_local() -> bool:
    """Return True when running in a local/dev environment.

    The function checks the LOCAL_DEV environment variable and the presence
    of a local .env file to determine whether the app is running locally.
    """
    return os.environ.get("LOCAL_DEV") == "1" or os.path.exists(".env")

if is_local():
    load_dotenv()

        
def create_thread(client: AIProjectClient, agent_id: str, user_message: str) -> Tuple[Optional[str], Optional[str]]:
    """Create a new thread, post a user message, and start processing a run.

    Args:
        client: An initialized Azure AIProjectClient.
        agent_id: The agent identifier to run.
        user_message: The user's message to post to the new thread.

    Returns:
        A tuple of (thread_id, run_id). Returns (None, None) on failure.
    """
    thread = client.agents.threads.create()
    client.agents.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_message,
    )
    run = client.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent_id)
    if getattr(run, "status", None) == "failed":
        st.error(f"Run failed: {getattr(run, 'last_error', None)}")
        return None, None
    return thread.id, getattr(run, "id", None)

def send_user_message(client: AIProjectClient, agent_id: str, user_message: str) -> Tuple[Optional[str], Optional[str]]:
    """Post a user message to an existing thread (or create one) and start a run.

    This function stores thread and run identifiers in Streamlit ``session_state``
    so that the conversation persists across reruns.

    Args:
        client: An initialized Azure AIProjectClient.
        agent_id: The agent identifier to run.
        user_message: The user's message to post.

    Returns:
        A tuple (thread_id, run_id). Either may be None on failure.
    """
    # create thread once per session
    if 'thread_id' not in st.session_state:
        thread = client.agents.threads.create()
        st.session_state['thread_id'] = thread.id

    # post user message to that thread
    client.agents.messages.create(
        thread_id=st.session_state['thread_id'],
        role="user",
        content=user_message,
    )

    # create and process a run for that message
    run = client.agents.runs.create_and_process(
        thread_id=st.session_state['thread_id'],
        agent_id=agent_id,
    )
    st.session_state['run_id'] = getattr(run, "id", None)
    return st.session_state.get('thread_id'), getattr(run, "id", None)

def get_responses(client: AIProjectClient, thread_id: str, run_id: str) -> List[str]:
    """Fetch assistant responses for a given thread/run.

    Args:
        client: An initialized Azure AIProjectClient.
        thread_id: The thread identifier.
        run_id: The run identifier to filter messages by.

    Returns:
        A list of response strings (may be empty).
    """
    messages = client.agents.messages.list(thread_id=thread_id, order=ListSortOrder.ASCENDING)
    responses: List[str] = []
    for message in messages:
        if getattr(message, "run_id", None) == run_id and getattr(message, "text_messages", None):
            # append the final text value for the message if present
            text_obj = message.text_messages[-1].text
            value = getattr(text_obj, "value", None)
            if value:
                responses.append(value)
    return responses

def safe_rerun() -> None:
    """Attempt to rerun the Streamlit app, with a safe fallback.

    Uses ``st.experimental_rerun()`` when available; otherwise calls
    ``st.stop()`` which ends the current run and allows Streamlit to render a
    fresh UI on the next interaction.
    """
    try:
        # prefer the API if available
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
        else:
            # immediate safe fallback
            st.stop()
    except Exception:
        # last-resort fallback
        st.stop()

def main() -> None:
    st.set_page_config(
        page_title="Dinner Generator",
        page_icon ="🍲"
    )

    apply_style_background()
    apply_style_blur()

    with st.sidebar:
        st.write("## Controls")
        st.write("Manage your session.")
        if st.button("Reset conversation", key="reset"):
            # remove only conversation-related keys (keep session alive)
            for k in ("thread_id", "run_id", "chat_history"):
                st.session_state.pop(k, None)
            # Ensure chat_history exists so the UI renders immediately
            st.session_state.setdefault("chat_history", [])
            # Prefer immediate rerun if available in Streamlit; otherwise continue the run so UI renders
            if hasattr(st, "experimental_rerun"):
                st.experimental_rerun()

    
    st.title("AI Dinner Planning Agent")

    agent_id = os.getenv("dingen_agent_id")

    if not agent_id:
        st.error("Missing environment variable: dingen_agent_id")
        return

    try:
        client = AIProjectClient(
            endpoint=os.getenv("dingen_azure_endpoint"),
            credential=DefaultAzureCredential(),
        )
    except Exception as e:
        st.error(f"Failed to create Azure client: {e}")
        return
    
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []

    user_input = st.chat_input("Hi! Let's plan your dinners 😀. Enter your requests here ...")

    
    if user_input:
        # Display user message in chat
        st.session_state['chat_history'].append(('user', user_input))
        # Send user message to agent and get a response
        thread_id, run_id = send_user_message(client, agent_id, user_input)
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