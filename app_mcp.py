# NB! not workng yes. Works with beta packages only, implies breaking changes.
# will wait until supported in stable release.

import os
import time

import streamlit as st
from azure.ai.agents.models import (
    ConnectedAgentTool,
    McpTool,
    RequiredMcpToolCall,
    SubmitToolApprovalAction,
    ToolApproval,
)
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

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

    # Connect to Azure AI Project
    endpoint = os.getenv("dingen_azure_endpoint")
    project_client = AIProjectClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential(),
    )

    # Initialize agent once per Streamlit session
    if "agent_id" not in st.session_state:
        # Get MCP server URL from environment
        mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")

        # Initialize MCP tool for Google Sheets
        mcp_tool = McpTool(
            server_label="google_sheets",
            server_url=mcp_server_url,
            allowed_tools=["get_recipes", "get_dinner_history", "search_recipes"],
        )

        # Try to get email agent, skip if it doesn't exist
        email_agent_id = os.getenv("email_agent_id")
        tools = mcp_tool.definitions

        if email_agent_id:
            try:
                # Beta SDK uses .get() instead of .get_agent()
                email_agent = project_client.agents.get(email_agent_id)
                connected_agent = ConnectedAgentTool(
                    id=email_agent.id,
                    name=email_agent.name,
                    description=email_agent.description,
                )
                tools = mcp_tool.definitions + connected_agent.definitions
                st.info(f"✅ Connected to email agent: {email_agent.name}")
            except Exception as e:
                st.warning(f"⚠️ Could not connect to email agent: {e}")
                st.info("Creating agent without email functionality")

        # Create main agent with MCP tool (+ email agent if available)
        # Beta SDK uses .create() instead of .create_agent()
        agent = project_client.agents.create(
            model="gpt-4o",
            name="dinner-planning-agent",
            instructions=primary_instructions,
            definition=primary_description,
            tools=tools,
        )

        st.session_state["agent_id"] = agent.id
        st.session_state["mcp_tool"] = mcp_tool
        st.success(f"✅ Created agent: {agent.id}")
    else:
        agent_id = st.session_state.get("agent_id")
        # Beta SDK uses .get() instead of .get_agent()
        agent = project_client.agents.get(agent_id)

    page = st.sidebar.selectbox("Select a page", ["Create Dinner Plan", "View Recipes"])

    if page == "Create Dinner Plan":
        st.title("🤖 AI Dinner Planning Agent 🫜")

        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []

        user_input = st.chat_input(
            "Hi! Let's plan your dinners 😀. Enter your requests here ..."
        )

        if user_input:
            st.session_state["chat_history"].append(("user", user_input))

            try:
                with st.spinner("Planning your dinners..."):
                    # Create thread if needed
                    if "thread_id" not in st.session_state:
                        thread = project_client.agents.threads.create()
                        st.session_state["thread_id"] = thread.id

                    # Post user message
                    project_client.agents.messages.create(
                        thread_id=st.session_state["thread_id"],
                        role="user",
                        content=user_input,
                    )

                    # Create run with MCP tool resources
                    mcp_tool = st.session_state.get("mcp_tool")
                    run = project_client.agents.runs.create(
                        thread_id=st.session_state["thread_id"],
                        agent_id=agent.id,
                        tool_resources=mcp_tool.resources if mcp_tool else None,
                    )

                    # Process run with approval handling
                    while run.status in ["queued", "in_progress", "requires_action"]:
                        time.sleep(1)
                        run = project_client.agents.runs.get(
                            thread_id=st.session_state["thread_id"], run_id=run.id
                        )

                        # Handle tool approval if required
                        if run.status == "requires_action" and isinstance(
                            run.required_action, SubmitToolApprovalAction
                        ):
                            tool_calls = (
                                run.required_action.submit_tool_approval.tool_calls
                            )
                            if tool_calls:
                                tool_approvals = []
                                for tool_call in tool_calls:
                                    if isinstance(tool_call, RequiredMcpToolCall):
                                        tool_approvals.append(
                                            ToolApproval(
                                                tool_call_id=tool_call.id,
                                                approve=True,
                                            )
                                        )

                                if tool_approvals:
                                    project_client.agents.runs.submit_tool_outputs(
                                        thread_id=st.session_state["thread_id"],
                                        run_id=run.id,
                                        tool_approvals=tool_approvals,
                                    )

                    # Get responses
                    if run.status == "completed":
                        messages = project_client.agents.messages.list(
                            thread_id=st.session_state["thread_id"]
                        )
                        for msg in messages:
                            if getattr(msg, "run_id", None) == run.id and getattr(
                                msg, "text_messages", None
                            ):
                                text_obj = msg.text_messages[-1].text
                                value = getattr(text_obj, "value", None)
                                if value:
                                    st.session_state["chat_history"].append(
                                        ("assistant", value)
                                    )
                    elif run.status == "failed":
                        error_msg = (
                            f"Run failed: {getattr(run, 'last_error', 'Unknown error')}"
                        )
                        st.session_state["chat_history"].append(
                            ("assistant", error_msg)
                        )

            except Exception as e:
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
        st.info("Showing recipes from Google Sheets")

        # Keep direct viewing capability (read-only)
        # recipes_data = utils.get_recipe_data(worksheet_index=0)
        # dinner_history = utils.get_recipe_data(worksheet_index=2)

        # st.subheader("All Recipes")
        # st.dataframe(recipes_data)
    #
    # st.subheader("Recent Dinner History (Last 14)")
    # st.dataframe(dinner_history.tail(14))

    with st.sidebar:
        st.write("## Controls")
        st.write("Manage your session.")

        if st.button("🔁 Reset conversation", key="reset"):
            for k in ("thread_id", "run_id", "chat_history"):
                st.session_state.pop(k, None)
            st.session_state.setdefault("chat_history", [])
            if hasattr(st, "experimental_rerun"):
                st.experimental_rerun()

        if st.button("❌ Delete agent", key="cleanup"):
            try:
                if st.session_state.get("agent_id"):
                    # Beta SDK uses .delete() instead of .delete_agent()
                    project_client.agents.delete(st.session_state["agent_id"])
                    st.success("Deleted agent")
                    for k in (
                        "agent_id",
                        "mcp_tool",
                        "thread_id",
                        "run_id",
                        "chat_history",
                    ):
                        st.session_state.pop(k, None)
                    if hasattr(st, "experimental_rerun"):
                        st.experimental_rerun()
            except Exception as e:
                st.error(f"Failed to delete agent: {e}")


if __name__ == "__main__":
    main()
