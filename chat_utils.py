# chat_utils.py
"""Chat interaction utilities."""
import streamlit as st
from azure.ai.agents.models import ListSortOrder
from azure.ai.projects import AIProjectClient


def send_user_message(
    client: AIProjectClient, agent_id: str, user_message: str
) -> tuple[str | None, str | None]:
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
    if "thread_id" not in st.session_state:
        thread = client.agents.threads.create()
        st.session_state["thread_id"] = thread.id

    # post user message to that thread
    client.agents.messages.create(
        thread_id=st.session_state["thread_id"],
        role="user",
        content=user_message,
    )

    # create and process a run for that message
    run = client.agents.runs.create_and_process(
        thread_id=st.session_state["thread_id"],
        agent_id=agent_id,
    )
    st.session_state["run_id"] = getattr(run, "id", None)
    return st.session_state.get("thread_id"), getattr(run, "id", None)


def get_responses(client: AIProjectClient, thread_id: str, run_id: str) -> list[str]:
    """Fetch assistant responses for a given thread/run.

    Args:
        client: An initialized Azure AIProjectClient.
        thread_id: The thread identifier.
        run_id: The run identifier to filter messages by.

    Returns:
        A list of response strings (may be empty).
    """
    messages = client.agents.messages.list(
        thread_id=thread_id, order=ListSortOrder.ASCENDING
    )
    responses: list[str] = []
    for message in messages:
        if getattr(message, "run_id", None) == run_id and getattr(
            message, "text_messages", None
        ):
            # append the final text value for the message if present
            text_obj = message.text_messages[-1].text
            value = getattr(text_obj, "value", None)
            if value:
                responses.append(value)
    return responses


def initialize_chat_history() -> None:
    """Initialize chat history in session state if not already present."""
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []


def handle_user_input(
    user_input: str, project_client: AIProjectClient, agent_id: str
) -> None:
    """Handle user input by sending message and processing response.

    Args:
        user_input: The user's message text.
        project_client: An initialized Azure AIProjectClient.
        agent_id: The agent identifier to run.
    """
    st.session_state["chat_history"].append({"role": "user", "content": user_input})

    try:
        with st.spinner("Sending your request to the agent..."):
            thread_id, run_id = send_user_message(project_client, agent_id, user_input)

        if thread_id and run_id:
            responses = get_responses(project_client, thread_id, run_id)
            for response in responses:
                st.session_state["chat_history"].append(
                    {"role": "assistant", "content": response}
                )
    except Exception as e:
        st.error(f"Error communicating with agent: {e}")
        st.session_state["chat_history"].append(
            {
                "role": "assistant",
                "content": "Sorry, I encountered an error. Please try again.",
            }
        )


def display_chat_history() -> None:
    """Render chat history messages."""
    for message in st.session_state.get("chat_history", []):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def reset_conversation() -> None:
    """Reset conversation state (thread, run, chat history)."""
    st.session_state.pop("thread_id", None)
    st.session_state.pop("run_id", None)
    st.session_state.pop("chat_history", None)
    st.rerun()
