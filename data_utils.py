"""Data preparation utilities for recipe and dinner history."""

import pandas as pd
import streamlit as st

import sheets_utils

# Constants
DINNER_HISTORY_LIMIT = 14
RECIPES_WORKSHEET_INDEX = 0
DINNER_HISTORY_WORKSHEET_INDEX = 2


@st.cache_data(ttl=300)  # Cache for 5 minutes
def prepare_recipe_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fetch and normalize recipe and dinner history data.

    Returns:
        Tuple of (recipes_data, dinner_history, combined_normalized_df).
    """
    # Fetch raw data
    recipes_data = sheets_utils.get_recipe_data(worksheet_index=RECIPES_WORKSHEET_INDEX)
    dinner_history = sheets_utils.get_recipe_data(
        worksheet_index=DINNER_HISTORY_WORKSHEET_INDEX, limit=DINNER_HISTORY_LIMIT
    )

    # Normalize for vector indexing
    dinner_history_norm = sheets_utils.normalize_df_for_indexing(
        dinner_history, source="dinner_history"
    )
    recipes_data_norm = sheets_utils.normalize_df_for_indexing(
        recipes_data, source="recipes"
    )

    # Combine
    combined_df = pd.concat(
        [recipes_data_norm, dinner_history_norm], ignore_index=True, sort=False
    )

    return recipes_data, dinner_history, combined_df
