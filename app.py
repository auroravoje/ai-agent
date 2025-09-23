import os
from dotenv import load_dotenv
import streamlit as st
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder

# Detect local vs deployed
def is_local():
    return os.environ.get("LOCAL_DEV") == "1" or os.path.exists(".env")

if is_local():
    load_dotenv()

        
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

def send_user_message(client, agent_id, user_message):
    """Create or reuse a thread for this Streamlit session, post the user message, and create a run.

    Stores `thread_id` and `run_id` in `st.session_state` so the same thread is reused across reruns.
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
    st.session_state['run_id'] = run.id
    return st.session_state['thread_id'], run.id

def get_responses(client, thread_id, run_id):
    messages = client.agents.messages.list(thread_id=thread_id, order=ListSortOrder.ASCENDING)
    responses = []
    for message in messages:
        if message.run_id == run_id and message.text_messages:
            responses.append(f"{message.role}: {message.text_messages[-1].text.value}")
    return responses 

def main():
    st.markdown("""
                <style> 
                .stApp { 
                    background: 
                linear-gradient(rgba(0,0,0,0.35), rgba(0,0,0,0.35)), 
                url("https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1920&q=80") 
                no-repeat center center fixed; 
                background-size: cover; } 
                </style>
    """, unsafe_allow_html=True)

    st.markdown(
    """
    <style>
    /* translucent overlay on whole app */
    .stApp, [data-testid="stAppViewContainer"] {
      position: relative;
    }
    .stApp::before,
    [data-testid="stAppViewContainer"]::before {
      content: "";
      position: fixed;
      inset: 0;
      background: rgba(255,255,255,0.40); /* adjust alpha for transparency */
      backdrop-filter: blur(1px);         /* subtle blur */
      z-index: 0;
      pointer-events: none;
    }
    /* push Streamlit content above the overlay */
    .reportview-container, .main, .block-container, 
    .stApp, [data-testid="stAppViewContainer"] > div {
      position: relative;
      z-index: 1;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
    with st.sidebar:
        st.write("## Controls")
        st.write("Manage your session.")
        if st.button("Reset conversation", key="reset"):
            for k in ("thread_id", "run_id", "chat_history"):
                st.session_state.pop(k, None)
            st.experimental_rerun()

    st.title("AI Dinner Planning Agent")

    agent_id = os.getenv("dingen_agent_id")


    client = AIProjectClient(
        endpoint=os.getenv("dingen_azure_endpoint"),
        credential=DefaultAzureCredential(),
    )
    
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []

    user_input = st.chat_input("Enter your message...")

    
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