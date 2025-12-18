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
                background-size: cover; 
                } 
                
                /* Dark mode - stronger overlay for better text contrast */
                @media (prefers-color-scheme: dark) {
                    .stApp {
                        background: 
                        linear-gradient(rgba(0,0,0,0.40), rgba(0,0,0,0.40)), 
                        url("https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1920&q=80") 
                        no-repeat center center fixed;
                        background-size: cover;
                    }
                }
                
                /* Light mode - lighter overlay */
                @media (prefers-color-scheme: light) {
                    .stApp {
                        background: 
                        linear-gradient(rgba(255,255,255,0.5), rgba(255,255,255,0.5)), 
                        url("https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1920&q=80") 
                        no-repeat center center fixed;
                        background-size: cover;
                    }
                }
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
      background: rgba(255,255,255,0.40); /* default for light mode */
      backdrop-filter: blur(1px);
      z-index: 0;
      pointer-events: none;
    }
    
    /* Dark mode - LIGHTER overlay since background already has one */
    @media (prefers-color-scheme: dark) {
        .stApp::before,
        [data-testid="stAppViewContainer"]::before {
            background: rgba(0,0,0,0.15);
            backdrop-filter: blur(2px);
        }
    }
    
    /* Light mode - keep it lighter */
    @media (prefers-color-scheme: light) {
        .stApp::before,
        [data-testid="stAppViewContainer"]::before {
            background: rgba(255,255,255,0.40);
            backdrop-filter: blur(1px);
        }
    }
    
    /* push Streamlit content above the overlay */
    .reportview-container, .main, .block-container, 
    .stApp, [data-testid="stAppViewContainer"] > div {
      position: relative;
      z-index: 1;
    }
    
    /* Text shadows only in dark mode */
    @media (prefers-color-scheme: dark) {
        .stMarkdown, .stText, p, h1, h2, h3, label {
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8);
        }
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


def apply_style_background_old():
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


def apply_style_blur_old():
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
