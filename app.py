import os
import warnings

import pandas as pd
import streamlit as st
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

import agent_utils
import chat_utils
import cleanup_utils
import data_utils
import utils
from streamlit_styles import apply_style_background, apply_style_blur

if utils.is_local():
    load_dotenv()
    # Use corporate CA bundle for SSL verification
    corp_cert_path = os.path.expanduser(os.getenv("CORP_CERT_PATH", ""))
    if corp_cert_path and os.path.exists(corp_cert_path):
        os.environ['SSL_CERT_FILE'] = corp_cert_path
        os.environ['REQUESTS_CA_BUNDLE'] = corp_cert_path
        os.environ['CURL_CA_BUNDLE'] = corp_cert_path
    else:
        warnings.warn("Corporate certificate bundle not found.")


def render_dinner_plan_page(project_client: AIProjectClient, agent_id: str) -> None:
    """Render the dinner planning chat interface.

    Args:
        project_client: An initialized Azure AIProjectClient.
        agent_id: The ID of the AI agent to use for chat interactions.
    """
    st.title("🤖 AI Dinner Planning Agent 🫜")

    chat_utils.initialize_chat_history()

    user_input = st.chat_input(
        "Hi! Let's plan your dinners 😀. Enter your requests here ..."
    )

    if user_input:
        chat_utils.handle_user_input(user_input, project_client, agent_id)

    chat_utils.display_chat_history()


def render_recipe_viewer_page(
    recipes_data: pd.DataFrame, dinner_history: pd.DataFrame
) -> None:
    """Render the recipe viewer page.

    Args:
        recipes_data: DataFrame containing recipe information.
        dinner_history: DataFrame containing dinner history.
    """
    st.title("📒 Recipe Viewer")
    st.info("Recipe viewing functionality is under development.")
    st.dataframe(recipes_data)
    st.title("Dinner History")
    st.dataframe(dinner_history)


def render_sidebar_controls(project_client: AIProjectClient) -> None:
    """Render sidebar control buttons.

    Args:
        project_client: An initialized Azure AIProjectClient.
    """
    with st.sidebar:
        st.write("## Controls")
        st.write("Manage your session.")

        if st.button("🔁 Reset conversation", key="reset"):
            chat_utils.reset_conversation()

        if st.button("❌ Delete resources", key="cleanup"):
            cleanup_utils.cleanup_and_clear_session(project_client)


def main() -> None:
    """Main application entry point."""
    st.set_page_config(page_title="Dinner Generator", page_icon="🍲")

    apply_style_background()
    apply_style_blur()

    if st.session_state.get("cleanup_done"):
        st.info(
            "Resources deleted. Please refresh the page to restart the application."
        )
        st.stop()

    
    endpoint = os.getenv("dingen_azure_endpoint")
    if not endpoint:
        st.error(
            "Azure endpoint not configured. Please set 'dingen_azure_endpoint' in your environment."
        )
        st.stop()

    # Configure SSL certificate for local development
    connection_kwargs = {
        "endpoint": endpoint,
        "credential": DefaultAzureCredential(),
    }
    
    if utils.is_local():
        corp_cert_path = os.path.expanduser(os.getenv("CORP_CERT_PATH", ""))
        if corp_cert_path and os.path.exists(corp_cert_path):
            connection_kwargs["connection_verify"] = corp_cert_path
        else:
            st.warning("⚠️ Corporate certificate not found. SSL verification may fail.")
    
    project_client = AIProjectClient(**connection_kwargs)

    with st.spinner("Loading recipe data..."):
        recipes_data, dinner_history, combined_df = data_utils.prepare_recipe_data()

    with st.spinner("Initializing AI agent..."):
        agent_id = agent_utils.get_or_create_agent(project_client, combined_df)
        agent = project_client.agents.get_agent(agent_id)

    page = st.sidebar.selectbox("Select a page", ["Create Dinner Plan", "View Recipes"])

    if page == "Create Dinner Plan":
        render_dinner_plan_page(project_client, agent.id)
    else:
        render_recipe_viewer_page(recipes_data, dinner_history)

    render_sidebar_controls(project_client)


if __name__ == "__main__":
    main()
