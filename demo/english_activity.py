from os.path import exists
import streamlit as st
import pandas as pd

reload = st.button("Update data")

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

st.dataframe(df)
