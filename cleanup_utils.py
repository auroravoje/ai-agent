import streamlit as st
from azure.ai.projects import AIProjectClient
from datetime import datetime, timedelta

def check_and_cleanup_inactive_agent(
    client: AIProjectClient,
    timeout_minutes: int = 10
) -> bool:
    """Check for inactivity and cleanup agent/vector store if timeout exceeded.
    
    Handles users who leave browser tabs open but inactive.
    
    Args:
        client: Azure AIProjectClient instance
        timeout_minutes: Minutes of inactivity before cleanup (default: 30)
    
    Returns:
        True if cleanup was performed, False otherwise
    """
    # Initialize last activity timestamp if not present
    if 'last_activity' not in st.session_state:
        st.session_state['last_activity'] = datetime.now()
        return False
    
    # Check if timeout exceeded
    time_since_activity = datetime.now() - st.session_state['last_activity']
    
    if time_since_activity > timedelta(minutes=timeout_minutes):
        # Cleanup if agent exists
        if 'agent_id' in st.session_state and st.session_state.get('agent_id'):
            try:
                # Delete vector store if exists
                if 'vector_store_id' in st.session_state and st.session_state.get('vector_store_id'):
                    client.agents.vector_stores.delete(st.session_state['vector_store_id'])
                    del st.session_state['vector_store_id']
                
                # Delete file if exists
                if 'file_id' in st.session_state and st.session_state.get('file_id'):
                    client.agents.files.delete(st.session_state['file_id'])
                    del st.session_state['file_id']
                
                # Delete agent
                client.agents.delete(st.session_state['agent_id'])
                del st.session_state['agent_id']
                
                # Clear related session state
                for key in ['thread_id', 'run_id', 'chat_history']:
                    if key in st.session_state:
                        del st.session_state[key]
                
                # Reset activity timestamp
                st.session_state['last_activity'] = datetime.now()
                return True
            except Exception as e:
                st.warning(f"Auto-cleanup failed: {e}")
                return False
    
    return False


def update_activity_timestamp():
    """Update the last activity timestamp to current time."""
    st.session_state['last_activity'] = datetime.now()


def cleanup_agent_resources(client: AIProjectClient) -> bool:
    """Cleanup agent, vector store, and files from session state.
    
    This is called both by manual delete button and automatic cleanup.
    Handles browser close scenario through Streamlit's session lifecycle.
    
    Args:
        client: Azure AIProjectClient instance
    
    Returns:
        True if cleanup was successful, False otherwise
    """
    try:
        # Delete vector store if exists
        if 'vector_store_id' in st.session_state and st.session_state.get('vector_store_id'):
            client.agents.vector_stores.delete(st.session_state['vector_store_id'])
            del st.session_state['vector_store_id']
        
        # Delete file if exists
        if 'file_id' in st.session_state and st.session_state.get('file_id'):
            client.agents.files.delete(st.session_state['file_id'])
            del st.session_state['file_id']
        
        # Delete agent
        if 'agent_id' in st.session_state and st.session_state.get('agent_id'):
            client.agents.delete(st.session_state['agent_id'])
            del st.session_state['agent_id']
        
        # Clear related session state
        for key in ['thread_id', 'run_id', 'chat_history']:
            if key in st.session_state:
                del st.session_state[key]
        
        return True
    except Exception as e:
        st.error(f"Cleanup failed: {e}")
        return False