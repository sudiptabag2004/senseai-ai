import streamlit as st


def update_query_params(key, dtype=str):
    if dtype == str:
        st.query_params[key] = st.session_state[key]
    elif dtype == int:
        st.query_params[key] = int(st.session_state[key])
    else:
        raise NotImplementedError(f"dtype {dtype} not implemented")
