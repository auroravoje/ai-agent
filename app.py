import os

import pandas as pd
import streamlit as st
from azure.ai.agents.models import ConnectedAgentTool, FilePurpose, FileSearchTool
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

import sheets_utils
import utils
from agent_instructions import primary_description, primary_instructions
from streamlit_styles import apply_style_background, apply_style_blur

# Detect local vs deployed
if utils.is_local():
    load_dotenv()


def main() -> None:
    st.set_page_config(page_title="Dinner Generator", page_icon="🍲")

    apply_style_background()
    apply_style_blur()

    recipes_data = sheets_utils.get_recipe_data()
    dinner_history = sheets_utils.get_recipe_data(worksheet_index=2, limit=14)
    dinner_history_norm = sheets_utils.normalize_df_for_indexing(
        dinner_history, source="dinner_history"
    )
    recipes_data_norm = sheets_utils.normalize_df_for_indexing(
        recipes_data, source="recipes"
    )
    combined_df = pd.concat(
        [recipes_data_norm, dinner_history_norm], ignore_index=True, sort=False
    )

    # Connect to Azure AI Project
    endpoint = os.getenv("dingen_azure_endpoint")
    project_client = AIProjectClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential(),
    )

    # Initialize agent + vector store + file once per Streamlit session
    if "agent_id" not in st.session_state:
        # create a temp json and upload + create vector store
        json_path = sheets_utils.df_to_temp_json(combined_df, ndjson=True)
        file = project_client.agents.files.upload(
            file_path=json_path, purpose=FilePurpose.AGENTS
        )
        st.session_state["file_id"] = getattr(file, "id", None) or file.get("id")

        vector_store = project_client.agents.vector_stores.create_and_poll(
            file_ids=[st.session_state["file_id"]],
            name=f"dingen_vectorstore_{int(pd.Timestamp.utcnow().timestamp())}",
        )
        st.session_state["vector_store_id"] = getattr(
            vector_store, "id", None
        ) or vector_store.get("id")

        # create agent pointing to the created vector store
        file_search = FileSearchTool(
            vector_store_ids=[st.session_state["vector_store_id"]]
        )

        # Create the agent with the file-search tool definition.

        email_agent = project_client.agents.get_agent(os.getenv("email_agent_id"))
        connected_agent = ConnectedAgentTool(
            id=email_agent.id,
            name=email_agent.name,
            description=email_agent.description,
        )
        # main agent
        agent = project_client.agents.create_agent(
            model="gpt-4o",
            name="dinner-planning-agent",
            instructions=primary_instructions,
            description=primary_description,
            tools=file_search.definitions + connected_agent.definitions,
            tool_resources=file_search.resources,
        )

        st.session_state["agent_id"] = getattr(agent, "id", None) or agent.get("id")

        # st.success(f"Created agent {st.session_state['agent_id']} and vector store {st.session_state['vector_store_id']}")
    else:
        # reuse ids stored in session state

        # file_id = st.session_state.get("file_id")
        # vector_store_id = st.session_state.get("vector_store_id")
        agent_id = st.session_state.get("agent_id")
        # optional: show current ids for debugging

        # st.write("Using agent:", agent_id)
        # st.write("Using vector store:", vector_store_id)

        # Fetch the agent object so agent.id is available for chat
        agent = project_client.agents.get_agent(agent_id)

    page = st.sidebar.selectbox("Select a page", ["Create Dinner Plan", "View Recipes"])

    if page == "Create Dinner Plan":

        st.title("🤖 AI Dinner Planning Agent 🫜")

        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []

        user_input = st.chat_input(
            "Hi! Let's plan your dinners 😀. Enter your requests here ..."
        )

        if user_input:
            # Display user message in chat
            st.session_state["chat_history"].append(("user", user_input))

            try:
                with st.spinner("Sending your request to the agent..."):
                    thread_id, run_id = utils.send_user_message(
                        project_client, agent.id, user_input
                    )
                # persist thread/run ids so the session can be reset or resumed
                if thread_id and run_id:
                    st.session_state["thread_id"] = thread_id
                    st.session_state["run_id"] = run_id
                    responses = utils.get_responses(project_client, thread_id, run_id)
                    for response in responses:
                        st.session_state["chat_history"].append(("assistant", response))

            except Exception as e:
                # Record an assistant message describing the failure so the user sees feedback in chat
                err_msg = f"Agent request failed: {e}"
                st.session_state["chat_history"].append(("assistant", err_msg))
                st.error(err_msg)
            # Display chat history
            for role, message in st.session_state["chat_history"]:
                if role == "user":
                    st.chat_message("user").markdown(message)
                else:
                    st.chat_message("assistant").markdown(message)

    elif page == "View Recipes":
        st.title("📒 Recipe Viewer")
        st.info("Recipe viewing functionality is under development.")
        st.dataframe(recipes_data)
        st.title("Dinner History")
        st.dataframe(dinner_history)

    with st.sidebar:
        st.write("## Controls")
        st.write("Manage your session.")
        if st.button("🔁 Reset conversation", key="reset"):
            # remove only conversation-related keys (keep session alive)
            for k in ("thread_id", "run_id", "chat_history"):
                st.session_state.pop(k, None)
            # Ensure chat_history exists so the UI renders immediately
            st.session_state.setdefault("chat_history", [])
            # Prefer immediate rerun if available in Streamlit; otherwise continue the run so UI renders
            if hasattr(st, "experimental_rerun"):
                st.experimental_rerun()

        # explicit cleanup button to delete created resources when you want
        if st.button("❌ Delete resources", key="cleanup"):
            deleted = {"agent": False, "vector_store": False, "file": False}
            try:
                if st.session_state.get("agent_id"):
                    project_client.agents.delete_agent(st.session_state["agent_id"])
                    deleted["agent"] = True
            except Exception as e:
                st.error(f"Failed to delete agent: {e}")
            try:
                if st.session_state.get("vector_store_id"):
                    vs_client = project_client.agents.vector_stores
                    if hasattr(vs_client, "delete"):
                        vs_client.delete(st.session_state["vector_store_id"])
                    elif hasattr(vs_client, "begin_delete"):
                        vs_client.begin_delete(
                            st.session_state["vector_store_id"]
                        ).result()
                    deleted["vector_store"] = True
            except Exception as e:
                st.error(f"Failed to delete vector store: {e}")
            try:
                if st.session_state.get("file_id"):
                    project_client.agents.files.delete(
                        file_id=st.session_state["file_id"]
                    )
                    deleted["file"] = True
            except Exception as e:
                st.error(f"Failed to delete file: {e}")
            # clear session state keys
            for k in (
                "agent_id",
                "vector_store_id",
                "file_id",
                "thread_id",
                "run_id",
                "chat_history",
            ):
                st.session_state.pop(k, None)
            st.success(f"Deleted: {deleted}")
            if hasattr(st, "experimental_rerun"):
                st.experimental_rerun()


if __name__ == "__main__":
    main()
