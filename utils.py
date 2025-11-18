import os

import streamlit as st
from azure.ai.agents.models import ListSortOrder
from azure.ai.projects import AIProjectClient


# Detect local vs deployed
def is_local() -> bool:
    """Return True when running in a local/dev environment."""
    is_deployed = os.environ.get("DEPLOYED") == "1" or not os.path.exists(".env")
    return not is_deployed


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
    return st.session_state.get("thread_id"), st.session_state.get("run_id")


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


def safe_rerun() -> None:
    """Attempt to rerun the Streamlit app, with a safe fallback."""
    try:
        st.experimental_rerun()
    except Exception:
        st.stop()
