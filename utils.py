import os

import streamlit as st


def is_local() -> bool:
    """Return True when running in a local/dev environment.

    Returns:
        True if running locally, False if deployed.
    """
    is_deployed = os.environ.get("DEPLOYED") == "1" or not os.path.exists(".env")
    return not is_deployed


def safe_rerun() -> None:
    """Attempt to rerun the Streamlit app, with a safe fallback.

    Tries to use experimental_rerun, falls back to stop if that fails.
    """
    try:
        st.experimental_rerun()
    except Exception:
        st.stop()
