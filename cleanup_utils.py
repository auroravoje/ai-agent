# cleanup_utils.py
"""Resource cleanup utilities."""
import streamlit as st
from azure.ai.projects import AIProjectClient

import utils


def cleanup_resources(project_client: AIProjectClient) -> dict[str, bool]:
    """Delete agent, vector store, and file.

    Args:
        project_client: Azure AI Project client.

    Returns:
        Dictionary with deletion status for each resource.
    """
    deleted = {"agent": False, "vector_store": False, "file": False}

    # Delete agent
    agent_id = st.session_state.get("agent_id")
    if agent_id:
        try:
            project_client.agents.delete_agent(agent_id)
            deleted["agent"] = True
            st.write("✓ Agent deleted successfully")
        except Exception as e:
            st.error(f"Failed to delete agent {agent_id}: {type(e).__name__}: {e}")

    # Delete vector store
    vector_store_id = st.session_state.get("vector_store_id")
    if vector_store_id:
        try:
            vs_client = project_client.agents.vector_stores

            # Try different delete methods
            if hasattr(vs_client, "delete_vector_store"):
                vs_client.delete_vector_store(vector_store_id)
            elif hasattr(vs_client, "delete"):
                vs_client.delete(vector_store_id)
            elif hasattr(vs_client, "begin_delete"):
                poller = vs_client.begin_delete(vector_store_id)
                poller.result()
            else:
                raise AttributeError(
                    f"No delete method found. Available methods: {dir(vs_client)}"
                )

            deleted["vector_store"] = True
            st.write("✓ Vector store deleted successfully")
        except Exception as e:
            st.error(
                f"Failed to delete vector store {vector_store_id}: {type(e).__name__}: {e}"
            )

    # Delete file
    file_id = st.session_state.get("file_id")
    if file_id:
        try:
            project_client.agents.files.delete(file_id=file_id)
            deleted["file"] = True
            st.write("✓ File deleted successfully")
        except Exception as e:
            st.error(f"Failed to delete file {file_id}: {type(e).__name__}: {e}")

    return deleted


def cleanup_and_clear_session(project_client: AIProjectClient) -> None:
    """Cleanup Azure resources and clear all session state.

    This permanently deletes the agent, vector store, and files from
    Azure, then clears all session state including conversation history.
    """
    # Show what we're about to delete
    resources_to_delete = []
    if st.session_state.get("agent_id"):
        resources_to_delete.append(f"agent ({st.session_state.get('agent_id')})")
    if st.session_state.get("vector_store_id"):
        resources_to_delete.append(
            f"vector_store ({st.session_state.get('vector_store_id')})"
        )
    if st.session_state.get("file_id"):
        resources_to_delete.append(f"file ({st.session_state.get('file_id')})")

    if not resources_to_delete:
        st.warning("No resources to delete.")
        return

    deleted = cleanup_resources(project_client)

    # Show summary
    success_count = sum(deleted.values())
    st.write(f"Deletion summary: {success_count}/{len(deleted)} resources deleted")

    # Clear session state keys
    for k in (
        "agent_id",
        "vector_store_id",
        "file_id",
        "thread_id",
        "run_id",
        "chat_history",
    ):
        st.session_state.pop(k, None)

    # Set flag to prevent recreation on rerun
    st.session_state["cleanup_done"] = True

    if success_count > 0:
        st.success("Session cleared. Restarting application...")
        utils.safe_rerun()
