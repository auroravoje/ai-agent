import streamlit as st


def apply_style_background():
    st.markdown(
        """
                <style> 
                .stApp { 
                    background: 
                linear-gradient(rgba(0,0,0,0.35), rgba(0,0,0,0.35)), 
                url("https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1920&q=80") 
                no-repeat center center fixed; 
                background-size: cover; } 
                </style>
    """,
        unsafe_allow_html=True,
    )


def apply_style_blur():
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
