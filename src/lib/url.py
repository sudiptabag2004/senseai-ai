import streamlit as st
import re
from unidecode import unidecode


def update_query_params(key, dtype=str):
    if dtype == str:
        st.query_params[key] = st.session_state[key]
    elif dtype == int:
        st.query_params[key] = int(st.session_state[key])
    else:
        raise NotImplementedError(f"dtype {dtype} not implemented")


def slugify(text: str) -> str:
    """
    Convert a string to a URL-friendly slug.
    Example: "Hello World! How are you?" -> "hello-world-how-are-you"

    Args:
        text: The string to convert

    Returns:
        A URL-friendly version of the string
    """
    # Convert to lowercase and normalize unicode characters
    text = str(text).lower()
    text = unidecode(text)

    # Replace any non-alphanumeric character with a hyphen
    text = re.sub(r"[^\w\s-]", "", text)

    # Replace all spaces or repeated hyphens with a single hyphen
    text = re.sub(r"[-\s]+", "-", text.strip())

    return text
