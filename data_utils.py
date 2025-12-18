"""Data preparation utilities for recipe and dinner history."""

import tempfile

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

    recipes_data = sheets_utils.get_recipe_data(worksheet_index=RECIPES_WORKSHEET_INDEX)
    dinner_history = sheets_utils.get_recipe_data(
        worksheet_index=DINNER_HISTORY_WORKSHEET_INDEX, limit=DINNER_HISTORY_LIMIT
    )

    dinner_history_norm = sheets_utils.normalize_df_for_indexing(
        dinner_history, source="dinner_history"
    )
    recipes_data_norm = sheets_utils.normalize_df_for_indexing(
        recipes_data, source="recipes"
    )

    combined_df = pd.concat(
        [recipes_data_norm, dinner_history_norm], ignore_index=True, sort=False
    )

    return recipes_data, dinner_history, combined_df


def df_to_temp_json(df: pd.DataFrame, ndjson: bool = True) -> str:
    """Serialize DataFrame to a temporary JSON file.

    Args:
        df: DataFrame to serialize.
        ndjson: If True, writes newline-delimited JSON (one JSON object per line).
            If False, writes a single JSON array.

    Returns:
        The file path to the temporary JSON file.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    if ndjson:
        # orient='records' + lines=True produces NDJSON
        df.to_json(tmp.name, orient="records", lines=True, force_ascii=False)
    else:
        df.to_json(tmp.name, orient="records", force_ascii=False)
    return tmp.name
