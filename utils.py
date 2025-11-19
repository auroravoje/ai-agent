import base64
import json
import os
import tempfile

import gspread
import pandas as pd
import streamlit as st
from azure.ai.agents.models import ListSortOrder
from azure.ai.projects import AIProjectClient
from oauth2client.service_account import ServiceAccountCredentials


def is_local() -> bool:
    """Return True when running in a local/dev environment."""
    is_deployed = os.environ.get("DEPLOYED") == "1" or not os.path.exists(".env")
    return not is_deployed


def _materialize_service_account_file() -> str:
    """
    Return a filesystem path to the Google service account JSON.
    Accepts any of these:
      1. google_app_credentials points to an existing file path.
      2. google_app_credentials holds raw JSON (starts with '{').
      3. google_app_credentials holds base64 of the JSON.
      4. google_app_credentials_json (alt var) with raw or base64 JSON.
    Writes a temp file if needed (cached in st.session_state to avoid duplicates).
    """
    cache_key = "_svc_acct_path"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    val_primary = os.getenv("google_app_credentials", "")
    val_alt = os.getenv("google_app_credentials_json", "")

    def try_decode(raw: str) -> str | None:
        raw = raw.strip()
        if not raw:
            return None
        # Raw JSON
        if raw.startswith("{"):
            return raw
        # Possibly base64
        try:
            decoded = base64.b64decode(raw).decode("utf-8")
            if decoded.strip().startswith("{"):
                return decoded
        except Exception:
            pass
        return None

    # 1. Existing file path?
    if val_primary and os.path.isfile(val_primary):
        st.session_state[cache_key] = val_primary
        return val_primary

    # 2/3: Try primary as JSON / base64
    json_text = try_decode(val_primary) or try_decode(val_alt)
    if not json_text:
        raise ValueError(
            "Google service account key not provided. Set google_app_credentials (path or JSON) "
            "or google_app_credentials_json (JSON/base64)."
        )

    # Validate JSON parses
    try:
        parsed = json.loads(json_text)
        if "client_email" not in parsed:
            raise ValueError("Service account JSON missing client_email.")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid service account JSON: {e}") from e

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    with open(tmp.name, "w", encoding="utf-8") as f:
        f.write(json_text)
    st.session_state[cache_key] = tmp.name
    return tmp.name


@st.cache_resource
def get_recipe_data(
    key_file: str | None = None,
    sheet_id: str | None = None,
    worksheet_index: int = 0,
) -> pd.DataFrame:
    """Fetch Google Sheets data and return it as a pandas DataFrame.

    This is a small helper for Streamlit apps. It uses a service account
    JSON key file to authenticate with the Google Sheets API and reads the
    chosen worksheet into a DataFrame. The function is cached with
    ``st.cache_resource`` to avoid repeated auth calls during a session.

    Args:
        key_file: Optional path to the service account JSON key file. If not
            provided the environment variable ``google_app_credentials`` is
            used.
        sheet_id: Optional Google Sheets ID. If not provided the environment
            variable ``google_sheet_id`` is used.
        worksheet_index: Index of the worksheet/tab to read (0-based).

    Returns:
        A pandas DataFrame containing the sheet records. If the sheet is
        empty, returns an empty DataFrame.

    Raises:
        FileNotFoundError: If the key file cannot be found.
        ValueError: If required identifiers are missing.
        Exception: Other errors from the Google API will propagate.
    """
    KEY_FILE = (
        key_file
        or os.getenv("google_app_credentials")
        or os.getenv("google_app_credentials_json")
    )
    sheet_id = sheet_id or os.getenv("google_sheet_id")

    if not sheet_id:
        raise ValueError("Google sheet id is not provided (google_sheet_id).")

    KEY_FILE = _materialize_service_account_file()

    if not KEY_FILE:
        raise ValueError(
            "Google service account key file path is not provided (google_app_credentials)."
        )
    if not sheet_id:
        raise ValueError("Google sheet id is not provided (google_sheet_id).")

    # Google Sheets scope
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    # Authenticate
    if not os.path.exists(KEY_FILE):
        raise FileNotFoundError(
            f"Google service account key file not found: {KEY_FILE}"
        )

    credentials = ServiceAccountCredentials.from_json_keyfile_name(KEY_FILE, scope)
    client = gspread.authorize(credentials)

    # Open the sheet and select worksheet by index
    spreadsheet = client.open_by_key(sheet_id)
    worksheets = spreadsheet.worksheets()
    if worksheet_index < 0 or worksheet_index >= len(worksheets):
        raise IndexError(
            f"worksheet_index {worksheet_index} out of range (0..{len(worksheets)-1})"
        )

    sheet = worksheets[worksheet_index]

    # Get all records as a DataFrame (returns empty DataFrame if no records)
    records = sheet.get_all_records()
    data = pd.DataFrame(records)
    return data


def df_to_temp_json(df: pd.DataFrame, ndjson: bool = True) -> str:
    """Serialize DataFrame to a temporary JSON file. Returns the file path.
    - ndjson=True writes newline-delimited JSON (one JSON object per line).
    - ndjson=False writes a single JSON array.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    if ndjson:
        # orient='records' + lines=True produces NDJSON
        df.to_json(tmp.name, orient="records", lines=True, force_ascii=False)
    else:
        df.to_json(tmp.name, orient="records", force_ascii=False)
    return tmp.name


def normalize_df_for_indexing(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Return a DataFrame with a consistent schema for vector indexing:
    - doc_id: stable string id
    - content: text to embed (concatenation of sensible text cols)
    - _source: marker for origin (recipes / dinner_history)
    - raw_metadata: dict of the original row values (kept for retrieval/filtering)
    """
    df = df.copy()
    df["_source"] = source
    # ensure doc_id
    if "id" in df.columns:
        df["doc_id"] = df["id"].astype(str)
    else:
        df["doc_id"] = df.index.astype(str)

    # choose text columns to combine into `content` (common recipe-like candidates)
    candidates = [
        "Rett",
        "Tidsforbruk min",
        "Lenke",
        "Sesong",
        "Preferanse",
        "uke",
        "dag",
    ]
    text_cols = [c for c in candidates if c in df.columns]
    if not text_cols:
        # fallback: use all object-like columns
        text_cols = [c for c in df.columns if df[c].dtype == object]

    if not text_cols:
        # last resort: stringify entire row
        df["content"] = df.astype(str).agg(" ".join, axis=1)
    else:
        # Fill NaN, cast everything to str, then join
        df["content"] = df[text_cols].fillna("").astype(str).agg(" ".join, axis=1)
    # preserve original metadata as a dict per row (excluding the computed content)
    meta_cols = [c for c in df.columns if c not in ("content",)]
    df["raw_metadata"] = df[meta_cols].apply(lambda r: r.to_dict(), axis=1)

    # return only the consistent set of columns expected by your uploader
    return df[["doc_id", "content", "_source", "raw_metadata"]]


########## chat utils ##########


def send_user_message(
    client: AIProjectClient, agent_id: str, user_message: str
) -> tuple[str | None, str | None]:
    """Post a user message to an existing thread (or create one) and start a run.

    This function stores thread and run identifiers in Streamlit ``session_state``
    so that the conversation persists across reruns.

    Args:
        client: An initialized Azure AIProjectClient.
        agent_id: The agent identifier to run.
        user_message: The user's message to post.

    Returns:
        A tuple (thread_id, run_id). Either may be None on failure.
    """
    # create thread once per session
    if "thread_id" not in st.session_state:
        thread = client.agents.threads.create()
        st.session_state["thread_id"] = thread.id

    # post user message to that thread
    client.agents.messages.create(
        thread_id=st.session_state["thread_id"],
        role="user",
        content=user_message,
    )

    # create and process a run for that message
    run = client.agents.runs.create_and_process(
        thread_id=st.session_state["thread_id"],
        agent_id=agent_id,
    )
    st.session_state["run_id"] = getattr(run, "id", None)
    return st.session_state.get("thread_id"), getattr(run, "id", None)


def get_responses(client: AIProjectClient, thread_id: str, run_id: str) -> list[str]:
    """Fetch assistant responses for a given thread/run.

    Args:
        client: An initialized Azure AIProjectClient.
        thread_id: The thread identifier.
        run_id: The run identifier to filter messages by.

    Returns:
        A list of response strings (may be empty).
    """
    messages = client.agents.messages.list(
        thread_id=thread_id, order=ListSortOrder.ASCENDING
    )
    responses: list[str] = []
    for message in messages:
        if getattr(message, "run_id", None) == run_id and getattr(
            message, "text_messages", None
        ):
            # append the final text value for the message if present
            text_obj = message.text_messages[-1].text
            value = getattr(text_obj, "value", None)
            if value:
                responses.append(value)
    return responses


def safe_rerun() -> None:
    """Attempt to rerun the Streamlit app, with a safe fallback."""
    try:
        st.experimental_rerun()
    except Exception:
        st.stop()
