from os.path import exists
import streamlit as st
import pandas as pd

reload_col, download_col, _ = st.columns([1, 1, 3])
reload = reload_col.button("Update data")

if reload:
    st.experimental_rerun()

if exists("/appdata"):
    root_dir = "/appdata"
else:
    root_dir = "."

df = pd.read_csv(f"{root_dir}/english_activity.csv")

unique_student_names = df["student name"].unique()
student_filter = st.multiselect("Select student", unique_student_names)

if student_filter:
    df = df[df["student name"].isin(student_filter)]

download_col.download_button(
    label="Download CSV",
    data=df.to_csv().encode("utf-8"),
    file_name="sensai_english_activity.csv",
    mime="text/csv",
)

st.dataframe(df)
