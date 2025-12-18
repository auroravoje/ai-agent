"""Agent initialization and management utilities."""

import os

import pandas as pd
import streamlit as st
from azure.ai.agents.models import ConnectedAgentTool, FilePurpose, FileSearchTool
from azure.ai.projects import AIProjectClient

import data_utils
from agent_instructions import primary_description, primary_instructions


def get_or_create_agent(
    project_client: AIProjectClient, combined_df: pd.DataFrame
) -> str:
    """Get existing agent or create new one.

    Args:
        project_client: Azure AI Project client.
        combined_df: Combined and normalized recipe data.

    Returns:
        Agent ID string.
    """
    if "agent_id" not in st.session_state:
        return initialize_agent(project_client, combined_df)
    return st.session_state["agent_id"]


def initialize_agent(project_client: AIProjectClient, combined_df: pd.DataFrame) -> str:
    """Initialize agent with vector store and email connection.

    Args:
        project_client: Azure AI Project client.
        combined_df: Combined and normalized recipe data.

    Returns:
        Agent ID string.
    """
    # Email agent (A2A connection)
    email_agent_id = os.getenv("email_agent_id")
    if email_agent_id:
        email_agent = project_client.agents.get_agent(email_agent_id)
        connected_agent = ConnectedAgentTool(
            id=email_agent.id,
            name=email_agent.name,
            description=email_agent.description,
        )
        email_tools = connected_agent.definitions
    else:
        email_tools = []
        st.warning("Email agent not configured")

    # File upload and vector store
    json_path = data_utils.df_to_temp_json(combined_df, ndjson=True)
    file = project_client.agents.files.upload(
        file_path=json_path, purpose=FilePurpose.AGENTS
    )
    file_id = getattr(file, "id", None) or file.get("id")

    vector_store = project_client.agents.vector_stores.create_and_poll(
        file_ids=[file_id],
        name=f"dingen_vectorstore_{int(pd.Timestamp.utcnow().timestamp())}",
    )
    vector_store_id = getattr(vector_store, "id", None) or vector_store.get("id")

    # Create file search tool
    file_search = FileSearchTool(vector_store_ids=[vector_store_id])

    # Create agent
    agent = project_client.agents.create_agent(
        model="gpt-4o",
        name="dinner-planning-agent",
        instructions=primary_instructions,
        description=primary_description,
        tools=file_search.definitions + email_tools,
        tool_resources=file_search.resources,
    )

    # Store in session state
    agent_id = getattr(agent, "id", None) or agent.get("id")
    st.session_state["agent_id"] = agent_id
    st.session_state["file_id"] = file_id
    st.session_state["vector_store_id"] = vector_store_id

    return agent_id
