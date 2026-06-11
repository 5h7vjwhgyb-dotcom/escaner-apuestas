import streamlit as st
import requests
import google.generativeai as genai

# --- DISEÑO ---
st.set_page_config(page_title="Analytics Pro", layout="wide")
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); color: white; }
    .card { background: rgba(255, 255, 255, 0.08); backdrop-filter: blur(10px); 
            padding: 20px; border-radius: 20px; border-left: 5px solid #00ff9d; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

st.title("⚽ Elite Sports Analytics")
