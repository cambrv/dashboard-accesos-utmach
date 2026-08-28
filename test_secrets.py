import streamlit as st
import json

def st_secrets_to_dict():
    try:
        # Use to_dict if available (Streamlit >= 1.30 might have it)
        if hasattr(st.secrets, "to_dict"):
            return st.secrets.to_dict()
        else:
            return dict(st.secrets)
    except Exception as e:
        print("Error:", e)
        return {}

d = st_secrets_to_dict()
print(type(d))
print(d.keys())
