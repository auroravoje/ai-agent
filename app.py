import os

import streamlit as st
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

import utils
from streamlit_styles import apply_style_background, apply_style_blur

if utils.is_local():
    load_dotenv()


def main() -> None:
    st.set_page_config(page_title="Dinner Generator", page_icon="🍲")

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

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    user_input = st.chat_input(
        "Hi! Let's plan your dinners 😀. Enter your requests here ..."
    )

    if user_input:
        # Display user message in chat
        st.session_state["chat_history"].append(("user", user_input))
        # Send user message to agent and get a response
        thread_id, run_id = utils.send_user_message(client, agent_id, user_input)
        if thread_id and run_id:
            responses = utils.get_responses(client, thread_id, run_id)
            for response in responses:
                # Append response to chat history
                st.session_state["chat_history"].append(("assistant", response))
            # Display chat history
            for role, message in st.session_state["chat_history"]:
                if role == "user":
                    st.chat_message("user").markdown(message)
                else:
                    st.chat_message("assistant").markdown(message)


if __name__ == "__main__":
    main()
