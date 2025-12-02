# sheets_utils.py - Shared Google Sheets utilities (no Streamlit dependency)
"""
Streamlit-free utilities for Google Sheets access.
Can be used by both the Streamlit app (via utils.py wrappers) and the MCP server.
"""
import base64
import json
import os
import tempfile

import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

# Module-level cache for non-Streamlit contexts
_service_account_cache: dict[str, str] = {}
_recipe_data_cache: dict[int, pd.DataFrame] = {}


def materialize_service_account_file(use_cache: dict | None = None) -> str:
    """
    Return filesystem path to Google service account JSON.

    Accepts any of these:
      1. google_app_credentials points to an existing file path.
      2. google_app_credentials holds raw JSON (starts with '{').
      3. google_app_credentials holds base64 of the JSON.
      4. google_app_credentials_json (alt var) with raw or base64 JSON.

    Args:
        use_cache: Optional cache dict. If None, uses module-level cache.

    Returns:
        Path to the service account JSON file.

    Raises:
        ValueError: If credentials cannot be found or are invalid.
    """
    cache = use_cache if use_cache is not None else _service_account_cache
    cache_key = "_svc_acct_path"

    if cache_key in cache:
        return cache[cache_key]

    val_primary = os.getenv("google_app_credentials", "")
    val_alt = os.getenv("google_app_credentials_json", "")

    def try_decode(raw: str) -> str | None:
        """Try to decode raw string as JSON or base64-encoded JSON."""
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

    # 1. Check if existing file path
    if val_primary and os.path.isfile(val_primary):
        cache[cache_key] = val_primary
        return val_primary

    # 2/3: Try primary as JSON / base64, then alt
    json_text = try_decode(val_primary) or try_decode(val_alt)
    if not json_text:
        raise ValueError(
            "Google service account key not provided. "
            "Set google_app_credentials (path or JSON) or google_app_credentials_json (JSON/base64)."
        )

    # Validate JSON parses correctly
    try:
        parsed = json.loads(json_text)
        if "client_email" not in parsed:
            raise ValueError("Service account JSON missing client_email.")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid service account JSON: {e}") from e

    # Write to temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    with open(tmp.name, "w", encoding="utf-8") as f:
        f.write(json_text)
    cache[cache_key] = tmp.name
    return tmp.name


def fetch_recipe_data(
    worksheet_index: int = 0,
    sheet_id: str | None = None,
    use_cache: dict | None = None,
    limit: int | None = None,  # Add limit parameter
) -> pd.DataFrame:
    """
    Fetch Google Sheets data without Streamlit dependencies.

    Args:
        worksheet_index: Index of worksheet to fetch (0-based).
        sheet_id: Optional Google Sheets ID. If not provided, uses google_sheet_id env var.
        use_cache: Optional cache dict. If None, uses module-level cache.
        limit: If provided, return only the last N rows (useful for history).

    Returns:
        DataFrame containing the sheet records. Empty DataFrame if no records.

    Raises:
        ValueError: If sheet_id is not provided.
        FileNotFoundError: If service account key file cannot be found.
        IndexError: If worksheet_index is out of range.
    """
    cache = use_cache if use_cache is not None else _recipe_data_cache

    # Use different cache key when limit is applied
    cache_key = f"{worksheet_index}_limit_{limit}" if limit else worksheet_index

    # Check cache first
    if cache_key in cache:
        return cache[cache_key]

    sheet_id = sheet_id or os.getenv("google_sheet_id")
    if not sheet_id:
        raise ValueError("google_sheet_id environment variable not set")

    key_file = materialize_service_account_file(use_cache)

    # Google Sheets scope
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    if not os.path.exists(key_file):
        raise FileNotFoundError(f"Key file not found: {key_file}")

    # Authenticate
    credentials = ServiceAccountCredentials.from_json_keyfile_name(key_file, scope)
    client = gspread.authorize(credentials)

    # Open spreadsheet and get worksheet
    spreadsheet = client.open_by_key(sheet_id)
    worksheets = spreadsheet.worksheets()

    if worksheet_index < 0 or worksheet_index >= len(worksheets):
        raise IndexError(
            f"worksheet_index {worksheet_index} out of range (0..{len(worksheets)-1})"
        )

    sheet = worksheets[worksheet_index]

    # Fetch data based on limit
    if limit:
        # Get all values first to know total rows
        all_values = sheet.get_all_values()
        if len(all_values) <= 1:  # Only header or empty
            data = pd.DataFrame()
        else:
            # Get header and last N data rows
            header = all_values[0]
            data_rows = (
                all_values[-limit:] if len(all_values) > limit else all_values[1:]
            )
            data = pd.DataFrame(data_rows, columns=header)
    else:
        # Get all records as DataFrame
        records = sheet.get_all_records()
        data = pd.DataFrame(records)

    # Cache the result
    cache[cache_key] = data

    return data
