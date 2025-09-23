import os
from dotenv import load_dotenv
import streamlit as st
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from functools import lru_cache
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

def get_responses(client, thread_id, run_id):
    messages = client.agents.messages.list(thread_id=thread_id, order=ListSortOrder.ASCENDING)
    responses = []
    for message in messages:
        if message.run_id == run_id and message.text_messages:
            # message.role may be an enum (e.g. MessageRole.AGENT) or a string like 'agent'
            role = getattr(message, 'role', '')
            try:
                # enum-like roles have a .name attribute
                role_name = role.name.lower() if hasattr(role, 'name') else str(role).lower()
            except Exception:
                role_name = str(role).lower()

            # Map Azure/SDK role names to user-facing names (keep 'assistant' for agent responses)
            if role_name in ('agent', 'assistant'):
                display_role = 'assistant'
            elif role_name == 'user':
                display_role = 'user'
            else:
                display_role = role_name

            responses.append(f"{display_role}: {message.text_messages[-1].text.value}")
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
        thread_id, run_id = create_thread(client, agent_id, user_input)
        if thread_id and run_id:
            responses = get_responses(client, thread_id, run_id)
            for response in responses:
                # Append response to chat history (response string like 'assistant: text' or just text)
                if isinstance(response, str) and ':' in response:
                    role_label, text = response.split(':', 1)
                    role_label = role_label.strip()
                    text = text.strip()
                else:
                    role_label = 'assistant'
                    text = response if isinstance(response, str) else str(response)
                st.session_state['chat_history'].append((role_label, text))

            # Display chat history using cards
            st.markdown('<div class="chat-stack">', unsafe_allow_html=True)
            for role, message in st.session_state['chat_history']:
                if role.lower() == 'user':
                    st.markdown(user_card(message), unsafe_allow_html=True)
                else:
                    st.markdown(assistant_card(message), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()